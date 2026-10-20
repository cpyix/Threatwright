"""Local web server for the GUI (ADR-0003, ADR-0007).

Binds to 127.0.0.1 by default (`--host` for containers/servers). Every API call
needs the custom header X-Threatwright, which other websites cannot send without a
CORS preflight this server never grants (CSRF). Host headers not explicitly allowed
are rejected (DNS rebinding) and a strict CSP is sent. In server mode HTTP Basic
Auth is on unless switched off explicitly (ADR-0013).
The server holds exactly one open project in memory; files are written only
on an explicit save.
"""

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from threatwright import __version__, archive, assistant, history
from threatwright.arc import ArcOverride, applicability, set_override
from threatwright.auth import REALM, BasicAuth, users_from
from threatwright.branding import PRODUCT_NAME, PROJECT_FILE
from threatwright.ci import render_ci
from threatwright.ci import target_path as ci_target_path
from threatwright.diagram import render_svg
from threatwright.library import Libraries, load_catalog, load_libraries
from threatwright.method import (
    Method,
    MethodError,
    asset_impact,
    evaluate,
    load_method,
    suggest_impact,
)
from threatwright.model.objects import (
    COLLECTIONS,
    Asset,
    DiagramLayout,
    ModelMeta,
    ModelObject,
    Threat,
    new_uuid,
)
from threatwright.model.refactor import rename_id
from threatwright.model.store import LoadError, Project, SubModel
from threatwright.oscal import OscalError, imported_libraries
from threatwright.oscal.project import import_into_project
from threatwright.render import (
    OUT_FORMATS,
    RenderError,
    build_documents,
    list_templates,
    preview_html,
)
from threatwright.rules import relative, validate
from threatwright.scaffold import ProjectExists, create_project
from threatwright.vcs import VcsError, changed_objects, release_tags

WEB_DIR = Path(__file__).parent / "web"
API_HEADER = "X-Threatwright"  # any value; its presence forces a CORS preflight (CSRF)
MODEL_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
MAX_BODY = 1 << 20
UPLOAD_PATH = "/api/project/upload"
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
    "form-action 'none'; frame-ancestors 'none'"
)
# Document preview: static HTML with inline styles, no scripts, framed by the app only.
PREVIEW_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
    "frame-ancestors 'self'; base-uri 'none'; form-action 'none'"
)


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """mtime and size of every YAML file, to detect changes from outside."""
    out = {}
    for path in root.rglob("*.yaml"):
        if "build" in path.relative_to(root).parts:
            continue
        st = path.stat()
        out[path.relative_to(root).as_posix()] = (st.st_mtime_ns, st.st_size)
    return out


class Session:
    """The one project open in this server, plus undo history."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.project: Project | None = None
        self.method: Method | None = None
        self.libs: Libraries | None = None
        self.files: dict[str, tuple[int, int]] = {}
        self.undo: list[dict[str, SubModel]] = []
        self.redo: list[dict[str, SubModel]] = []
        self.dirty = False
        self.changes = 0  # counts edits; autosave only when it moved
        self.autosaved = 0
        self.pending: str | None = None  # unsaved autosave found when opening

    def open(self, root: Path) -> None:
        project = Project.load(root)
        self.project = project
        try:
            self.method = load_method(project.root, project.config)
        except MethodError:
            self.method = None  # reported by validate()
        self.libs = load_libraries(project.config.libraries, project.root)
        self.files = _snapshot(project.root)
        self.undo.clear()
        self.redo.clear()
        self.dirty = False
        self.changes = self.autosaved = 0
        newest = history.entries(project.root)[:1]
        self.pending = newest[0].id if newest and newest[0].kind == "auto" else None
        if self.pending:
            # marks the unsaved autosave as seen, so it is offered once, not on every open
            history.record(project.root, project.models, "open")

    def changed(self) -> None:
        self.changes += 1
        self.dirty = True

    def require(self) -> Project:
        if self.project is None:
            raise HTTPException(409, "no project open")
        return self.project

    def model(self, name: str) -> SubModel:
        sub = self.require().models.get(name)
        if sub is None:
            raise HTTPException(404, f"model '{name}' not found")
        return sub

    def checkpoint(self) -> None:
        """Remember the state before a change (undo/redo within the session)."""
        project = self.require()
        self.undo.append({k: _copy_model(v) for k, v in project.models.items()})
        del self.undo[:-100]
        self.redo.clear()
        self.changed()

    def save(self) -> list[str]:
        project = self.require()
        written = project.save()
        self.files = _snapshot(project.root)
        self.dirty = False
        self.pending = None
        if written:  # an unchanged save adds no version
            history.record(project.root, project.models, "save")
        self.autosaved = self.changes
        return [p.relative_to(project.root).as_posix() for p in written]

    def autosave(self) -> history.Entry | None:
        """Snapshot unsaved edits into the history; None when there is nothing new."""
        project = self.require()
        if not self.dirty or self.changes == self.autosaved:
            return None
        self.autosaved = self.changes
        return history.record(project.root, project.models, "auto")


def _copy_model(sub: SubModel) -> SubModel:
    return SubModel(
        sub.name,
        sub.meta.model_copy(deep=True),
        sub.layout.model_copy(deep=True),
        {
            c: {i: o.model_copy(deep=True) for i, o in objs.items()}
            for c, objs in sub.objects.items()
        },
    )


def _collection(name: str) -> type[ModelObject]:
    cls = COLLECTIONS.get(name)
    if cls is None:
        raise HTTPException(404, f"unknown collection '{name}'")
    return cls


def _parse[T: ModelObject](cls: type[T], data: Any) -> T:
    try:
        return cls.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(422, json.loads(exc.json(include_url=False))) from exc


def recent_file() -> Path:
    """Per-user list of recently opened projects (not model data)."""
    override = os.environ.get("THREATWRIGHT_CONFIG_DIR")
    if override:
        return Path(override) / "recent.json"
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / PRODUCT_NAME.lower() / "recent.json"


def _recent(add: Path | None = None) -> list[str]:
    path = recent_file()
    try:
        items: list[str] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        items = []
    if add is not None:
        items = [str(add.resolve())] + [i for i in items if i != str(add.resolve())]
        items = items[:10]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        except OSError:
            pass  # recent list is a convenience only
    return [i for i in items if (Path(i) / PROJECT_FILE).exists()]


def pick_folder(title: str, initial: str | None = None) -> str | None:
    """Native folder dialog on the local machine; None when cancelled.

    Linux prefers zenity/kdialog (desktop-native), macOS uses osascript (Tk must run on
    the main thread there), otherwise Tk, which uses the Explorer dialog on Windows.
    Raises RuntimeError without a desktop (container, SSH).
    """
    # absolute, so a value like "--help" can never be read as a dialog option
    start = os.path.abspath(initial or Path.home())
    if sys.platform == "darwin":
        # title and folder as argv, never spliced into the script; choose folder fails on a
        # missing default location, so that falls back to the home folder
        script = (
            "on run argv",
            "try",
            "set startAt to (POSIX file (item 2 of argv)) as alias",
            "on error",
            "set startAt to path to home folder",
            "end try",
            "activate",
            "POSIX path of (choose folder with prompt (item 1 of argv) default location startAt)",
            "end run",
        )
        args = [arg for line in script for arg in ("-e", line)]
        # cancelling exits non-zero with empty stdout
        result = subprocess.run(  # noqa: S603
            ["/usr/bin/osascript", *args, title, start], capture_output=True, text=True, check=False
        )
        picked = result.stdout.strip()
        return os.path.normpath(picked) if picked else None
    if sys.platform.startswith("linux"):
        for cmd in (
            [
                "zenity",
                "--file-selection",
                "--directory",
                f"--title={title}",
                f"--filename={start}/",
            ],
            ["kdialog", "--getexistingdirectory", start, "--title", title],
        ):
            if shutil.which(cmd[0]):
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
                return result.stdout.strip() or None
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        raise RuntimeError("no folder dialog available") from exc
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError("no desktop available for a folder dialog") from exc
    try:
        root.withdraw()
        root.attributes("-topmost", True)  # otherwise the dialog may open behind the browser
        path = filedialog.askdirectory(parent=root, title=title, initialdir=start, mustexist=False)
    finally:
        root.destroy()
    return path or None


def create_app(
    port: int | None = None,
    project: Path | None = None,
    hosts: frozenset[str] = frozenset(),
    root: Path | None = None,
    users: dict[str, str] | None = None,
) -> FastAPI:
    """`hosts`: extra host names accepted on any port (server/container use).
    `root`: server mode; project and import paths from clients must stay inside it.
    `users`: name -> password hash for HTTP Basic Auth; None = no login."""
    basic = BasicAuth(users) if users else None
    app = FastAPI(title=PRODUCT_NAME, docs_url=None, redoc_url=None, openapi_url=None)
    jail = root.resolve() if root is not None else None

    def client_path(raw: str) -> Path:
        """Locally the user may pick any folder; on a server only inside `root` (ADR-0013)."""
        if jail is None:
            return Path(raw)
        # realpath resolves ".." and symlinks; relative paths count from root, absolute ones
        # replace it. One prefix check on the result, before any use of the path.
        base = str(jail)
        candidate = os.path.realpath(os.path.join(base, raw))
        if candidate == base:
            return jail
        if not candidate.startswith(base + os.sep):
            raise HTTPException(403, "path is outside the folder this server works on")
        return Path(candidate)

    def local_only() -> None:
        if jail is not None:
            raise HTTPException(501, "not available when Threatwright runs as a server")

    def server_only() -> Path:
        if jail is None:
            raise HTTPException(501, "only when Threatwright runs as a server")
        return jail

    session = Session()
    app.state.session = session
    if project is not None:
        try:
            session.open(project)
            _recent(project)
        except LoadError as exc:
            print(f"warning: {exc}", flush=True)  # GUI starts on the start page instead

    @app.middleware("http")
    async def guard(request: Request, call_next: Any) -> Response:
        host = request.headers.get("host", "")
        allowed = (
            {"127.0.0.1", "localhost"}
            if port is None
            else {f"127.0.0.1:{port}", f"localhost:{port}"}
        )
        if port is None:
            host = host.split(":")[0]
        if host not in allowed and host.rsplit(":", 1)[0] not in hosts:
            return JSONResponse({"detail": "forbidden host"}, status_code=403)
        if basic is not None and not basic.check(request.headers.get("authorization")):
            return Response("login required", status_code=401, headers={"WWW-Authenticate": REALM})
        if request.url.path.startswith("/api/"):
            if API_HEADER.lower() not in request.headers:  # cross-site requests cannot set it
                return JSONResponse({"detail": f"missing {API_HEADER} header"}, status_code=403)
            limit = archive.MAX_UPLOAD if request.url.path == UPLOAD_PATH else MAX_BODY
            if int(request.headers.get("content-length") or 0) > limit:
                return JSONResponse({"detail": "request too large"}, status_code=413)
        response: Response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    # --- app and project --------------------------------------------------------

    @app.get("/api/app")
    def app_info() -> dict[str, Any]:
        return {
            "product": PRODUCT_NAME,
            "version": __version__,
            "server": jail is not None,
            # the recent list holds paths of this machine; on a server the workspace replaces it
            "recent": [] if jail is not None else _recent(),
        }

    @app.get("/api/workspace")
    def workspace() -> dict[str, Any]:
        """Server mode: the projects in the folder this server works on."""
        return {"projects": archive.projects_in(server_only())}

    @app.post(UPLOAD_PATH)
    async def upload_project(request: Request, folder: str) -> dict[str, Any]:
        """Server mode: a project zipped on the user's machine becomes a folder in the workspace."""
        workspace_root = server_only()
        data = bytearray()
        async for chunk in request.stream():  # also bounded without a content-length header
            data += chunk
            if len(data) > archive.MAX_UPLOAD:
                raise HTTPException(413, f"archive larger than {archive.MAX_UPLOAD >> 20} MB")
        with session.lock:
            try:
                # unpack confines the folder to the workspace itself
                session.open(archive.unpack(bytes(data), workspace_root, folder))
            except (archive.ArchiveError, LoadError, OSError) as exc:
                raise HTTPException(400, str(exc)) from exc
            return project_info()

    @app.get("/api/project/download")
    def download_project() -> Response:
        """The open project as .zip (the saved state), e.g. to continue locally."""
        with session.lock:
            if session.dirty:
                raise HTTPException(409, "save your changes before downloading")
            root = session.require().root
            data = archive.pack(root)
        name = f"{root.resolve().name}.zip"
        return Response(
            data,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )

    @app.post("/api/project/open")
    def open_project(body: dict[str, str]) -> dict[str, Any]:
        path = client_path(body.get("path", ""))
        with session.lock:
            try:
                session.open(path)
            except (LoadError, OSError) as exc:
                raise HTTPException(400, str(exc)) from exc
            _recent(path)
            return project_info()

    dialog_lock = threading.Lock()

    @app.post("/api/pick-folder")
    def pick_folder_endpoint(body: dict[str, str]) -> dict[str, str | None]:
        local_only()  # would open a dialog on the server's desktop
        if not dialog_lock.acquire(blocking=False):
            raise HTTPException(409, "a folder dialog is already open")
        try:
            return {"path": pick_folder(body.get("title") or PRODUCT_NAME, body.get("initial"))}
        except RuntimeError as exc:
            raise HTTPException(501, str(exc)) from exc
        finally:
            dialog_lock.release()

    @app.post("/api/project/new")
    def new_project(body: dict[str, str]) -> dict[str, Any]:
        template = body.get("template", "tr")
        language = body.get("language", "de")
        if template not in ("tr", "empty") or language not in ("de", "en"):
            raise HTTPException(422, "template: tr|empty, language: de|en")
        path = client_path(body.get("path", ""))
        with session.lock:
            try:
                create_project(path, template, body.get("name") or None, language)  # type: ignore[arg-type]
                session.open(path)
            except (ProjectExists, LoadError, OSError) as exc:
                raise HTTPException(400, str(exc)) from exc
            _recent(path)
            return project_info()

    @app.get("/api/catalog/{name}")
    def catalog(name: str) -> dict[str, Any]:
        if name not in ("cra", "attack-ics", "emb3d", "iec62443"):
            raise HTTPException(404, "unknown catalog")
        return load_catalog(name).model_dump(mode="json")

    @app.get("/api/project")
    def project_info() -> dict[str, Any]:
        with session.lock:
            project = session.require()
            return {
                "root": str(project.root.resolve()),
                "config": project.config.model_dump(mode="json"),
                "custom_fields": project.custom_fields.model_dump(mode="json"),
                "models": {
                    name: {
                        "title": sub.meta.title,
                        "counts": {c: len(o) for c, o in sub.objects.items()},
                    }
                    for name, sub in project.models.items()
                },
                "dirty": session.dirty,
                "can_undo": bool(session.undo),
                "can_redo": bool(session.redo),
            }

    @app.get("/api/method")
    def method_info() -> dict[str, Any]:
        with session.lock:
            session.require()
            if session.method is None:
                raise HTTPException(409, "method invalid, see validation")
            return session.method.model_dump(mode="json")

    @app.post("/api/models")
    def create_model(body: dict[str, str]) -> dict[str, Any]:
        name = body.get("name", "")
        if not MODEL_NAME.match(name):
            raise HTTPException(422, "model name: lowercase letters, digits, - and _")
        with session.lock:
            project = session.require()
            if name in project.models:
                raise HTTPException(409, f"model '{name}' exists")
            session.checkpoint()
            project.models[name] = SubModel(name, ModelMeta(title=body.get("title") or name))
            return project_info()

    # --- model content ------------------------------------------------------------

    def model_payload(sub: SubModel) -> dict[str, Any]:
        project = session.require()
        threats = {i: t for i, t in sub.objects["threats"].items() if isinstance(t, Threat)}
        assets = {i: a for i, a in sub.objects["assets"].items() if isinstance(a, Asset)}
        evaluations: dict[str, Any] = {}
        if session.method is not None:
            for tid, t in threats.items():
                evaluations[tid] = _evaluation(session.method, t, assets, project)
        return {
            "name": sub.name,
            "meta": sub.meta.model_dump(mode="json"),
            "layout": sub.layout.model_dump(mode="json"),
            "objects": {
                c: [o.model_dump(mode="json") for o in objs.values()]
                for c, objs in sub.objects.items()
            },
            "evaluations": evaluations,
            "max_risks": _max_risks(evaluations, sub),
            "asset_impacts": {aid: asset_impact(session.method, assets, aid) for aid in assets}
            if session.method
            else {},
        }

    @app.get("/api/models/{name}")
    def get_model(name: str) -> dict[str, Any]:
        with session.lock:
            return model_payload(session.model(name))

    @app.put("/api/models/{name}/meta")
    def put_meta(name: str, body: dict[str, Any]) -> dict[str, Any]:
        with session.lock:
            sub = session.model(name)
            try:
                meta = ModelMeta.model_validate(body)
            except ValidationError as exc:
                raise HTTPException(422, json.loads(exc.json(include_url=False))) from exc
            if meta != sub.meta:
                session.checkpoint()
                sub.meta = meta
            return model_payload(sub)

    @app.post("/api/models/{name}/evaluate")
    def evaluate_draft(name: str, body: dict[str, Any]) -> dict[str, Any]:
        """Live assessment of an unsaved threat form."""
        with session.lock:
            sub = session.model(name)
            if session.method is None:
                raise HTTPException(409, "method invalid, see validation")
            draft = _parse(Threat, {**body, "id": body.get("id") or "T-0000"})
            assets = {i: a for i, a in sub.objects["assets"].items() if isinstance(a, Asset)}
            return _evaluation(session.method, draft, assets, session.require())

    @app.post("/api/models/{name}/{collection}")
    def create_object(name: str, collection: str, body: dict[str, Any]) -> dict[str, Any]:
        cls = _collection(collection)
        with session.lock:
            sub = session.model(name)
            data = {**body, "id": sub.next_id(collection), "uuid": str(new_uuid())}
            obj = _parse(cls, data)
            session.checkpoint()
            sub.objects[collection][obj.id] = obj
            return {"object": obj.model_dump(mode="json"), "model": model_payload(sub)}

    @app.put("/api/models/{name}/{collection}/{obj_id}")
    def put_object(name: str, collection: str, obj_id: str, body: dict[str, Any]) -> dict[str, Any]:
        cls = _collection(collection)
        with session.lock:
            sub = session.model(name)
            current = sub.objects[collection].get(obj_id)
            if current is None:
                raise HTTPException(404, f"{obj_id} not found")
            obj = _parse(cls, {**body, "id": obj_id, "uuid": str(current.uuid)})
            if obj != current:
                session.checkpoint()
                sub.objects[collection][obj_id] = obj
            return {"object": obj.model_dump(mode="json"), "model": model_payload(sub)}

    @app.post("/api/models/{name}/{collection}/{obj_id}/rename")
    def rename_object(name: str, collection: str, obj_id: str, body: dict[str, str]) -> Any:
        _collection(collection)
        with session.lock:
            project = session.require()
            session.model(name)
            new_id = body.get("id", "")
            snapshot = {k: _copy_model(v) for k, v in project.models.items()}
            try:
                updated = rename_id(project, name, collection, obj_id, new_id)
            except KeyError as exc:
                raise HTTPException(404, f"{obj_id} not found") from exc
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            session.undo.append(snapshot)
            session.redo.clear()
            session.changed()
            return {"id": new_id, "updated": updated, "model": model_payload(project.models[name])}

    @app.delete("/api/models/{name}/{collection}/{obj_id}")
    def delete_object(name: str, collection: str, obj_id: str) -> dict[str, Any]:
        _collection(collection)
        with session.lock:
            sub = session.model(name)
            if obj_id not in sub.objects[collection]:
                raise HTTPException(404, f"{obj_id} not found")
            session.checkpoint()
            del sub.objects[collection][obj_id]
            return model_payload(sub)

    # --- diagram, library and assistant (M4) ----------------------------------------

    def libs() -> Libraries:
        if session.libs is None:
            raise HTTPException(409, "no project open")
        return session.libs

    def need_method() -> Method:
        if session.method is None:
            raise HTTPException(409, "method invalid, see validation")
        return session.method

    @app.get("/api/library")
    def library_info() -> dict[str, Any]:
        with session.lock:
            return {
                "elements": [e.model_dump(mode="json") for e in libs().elements.values()],
                "issues": len(libs().issues),
            }

    @app.put("/api/models/{name}/layout")
    def put_layout(name: str, body: dict[str, Any]) -> dict[str, Any]:
        with session.lock:
            sub = session.model(name)
            try:
                # notes are optional in the body, so a positions-only update keeps them
                notes = body.get("notes", sub.layout.model_dump(mode="json")["notes"])
                nodes = body.get("nodes", {})
                layout = DiagramLayout.model_validate({"nodes": nodes, "notes": notes})
            except ValidationError as exc:
                raise HTTPException(422, json.loads(exc.json(include_url=False))) from exc
            if layout != sub.layout:
                session.checkpoint()
                sub.layout = layout
            return {"ok": True}

    @app.post("/api/models/{name}/add/element")
    def add_element_endpoint(name: str, body: dict[str, Any]) -> dict[str, Any]:
        with session.lock:
            sub = session.model(name)
            if body.get("type") not in libs().elements:
                raise HTTPException(422, "unknown element type")
            session.checkpoint()
            try:
                element = assistant.add_element(
                    sub,
                    libs(),
                    session.require().config,
                    body["type"],
                    title=body.get("title") or None,
                    zone=body.get("zone"),
                    position=(float(body.get("x", 0)), float(body.get("y", 0))),
                )
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            return {"id": element.id, "model": model_payload(sub)}

    @app.post("/api/models/{name}/add/flow")
    def add_flow_endpoint(name: str, body: dict[str, Any]) -> dict[str, Any]:
        with session.lock:
            sub = session.model(name)
            session.checkpoint()
            try:
                flow = assistant.add_flow(
                    sub,
                    libs(),
                    session.require().config,
                    str(body.get("source")),
                    str(body.get("target")),
                    body.get("type") or None,
                )
            except (KeyError, ValueError) as exc:
                raise HTTPException(422, str(exc)) from exc
            return {"id": flow.id, "model": model_payload(sub)}

    @app.get("/api/models/{name}/assistant/{target}")
    def assistant_get(name: str, target: str) -> dict[str, Any]:
        with session.lock:
            sub = session.model(name)
            try:
                cats = assistant.suggestions(
                    sub, libs(), need_method(), session.require().config, target
                )
            except KeyError as exc:
                raise HTTPException(404, f"{target} not found") from exc
            return {"target": target, "categories": {s: asdict(c) for s, c in cats.items()}}

    @app.post("/api/models/{name}/assistant/{target}")
    def assistant_adopt(name: str, target: str, body: dict[str, str]) -> dict[str, Any]:
        with session.lock:
            sub = session.model(name)
            if body.get("template") not in libs().threats:
                raise HTTPException(422, "unknown threat template")
            session.checkpoint()
            try:
                threat = assistant.adopt_threat(
                    sub, libs(), session.require().config, body["template"], target
                )
            except KeyError as exc:
                raise HTTPException(404, f"{target} not found") from exc
            return {"id": threat.id, "model": model_payload(sub)}

    @app.get("/api/models/{name}/coverage")
    def coverage(name: str) -> list[dict[str, Any]]:
        with session.lock:
            return [asdict(r) for r in assistant.coverage(session.model(name), need_method())]

    @app.get("/api/models/{name}/diagram.svg")
    def diagram_svg(name: str) -> Response:
        with session.lock:
            sub = session.model(name)
            risks = _max_risks(model_payload(sub)["evaluations"], sub)
            return Response(render_svg(sub, risks), media_type="image/svg+xml")

    # --- Git (optional) ----------------------------------------------------------------

    @app.get("/api/vcs/changed")
    def vcs_changed(since: str = "") -> dict[str, Any]:
        """Objects changed since HEAD or a revision (e.g. the last release tag)."""
        with session.lock:
            root = session.require().root
        try:
            changed = changed_objects(root, since or None)
            tags = [asdict(t) for t in release_tags(root)]
        except VcsError:
            return {"available": False, "models": {}, "tags": []}
        return {
            "available": True,
            "models": {m: sorted(ids) for m, ids in changed.items()},
            "tags": tags,
        }

    # --- OSCAL import and ARC applicability (M6) ------------------------------------

    @app.get("/api/oscal/imported")
    def oscal_imported() -> list[dict[str, Any]]:
        with session.lock:
            root = session.require().root
            origin = session.libs.origin if session.libs else {}
            counts: dict[str, int] = {}
            for (_, _), lib in origin.items():
                counts[lib] = counts.get(lib, 0) + 1
        return [
            {
                "library": item["name"],
                "title": item.get("title", ""),
                "version": item.get("version", ""),
                "source": item.get("source", ""),
                "entries": counts.get(item["name"], 0),
            }
            for item in imported_libraries(root)
        ]

    @app.post("/api/oscal/import")
    def oscal_import(body: dict[str, str]) -> dict[str, Any]:
        kind = body.get("as", "catalog")
        if kind not in ("catalog", "profile", "component"):
            raise HTTPException(422, "as: catalog|profile|component")
        with session.lock:
            root = session.require().root
            if session.dirty:
                raise HTTPException(409, "save your changes before importing")
            try:
                written = import_into_project(root, client_path(body.get("path", "")), kind)  # type: ignore[arg-type]
            except OscalError as exc:
                raise HTTPException(422, "\n".join(str(i) for i in exc.issues) or str(exc)) from exc
            except (ValueError, OSError) as exc:
                raise HTTPException(400, str(exc)) from exc
            session.open(root)
            return {"written": str(written)}

    @app.get("/api/models/{name}/controls")
    def controls(name: str) -> list[dict[str, Any]]:
        with session.lock:
            project = session.require()
            session.model(name)
            try:
                result = applicability(project, name, libs())
            except MethodError as exc:
                raise HTTPException(409, str(exc)) from exc
            return [asdict(c) for c in result]

    @app.put("/api/arc/{name}/{measure_id}")
    def control_override(name: str, measure_id: str, body: dict[str, Any] | None = None) -> Any:
        """Manual ARC decision with rationale; empty body removes the override."""
        with session.lock:
            root = session.require().root
            session.model(name)
            try:
                override = ArcOverride.model_validate(body) if body else None
            except ValidationError as exc:
                raise HTTPException(422, json.loads(exc.json(include_url=False))) from exc
            set_override(root, name, measure_id, override)
            return controls(name)

    # --- documents (M5) ----------------------------------------------------------------
    # Documents are rendered from the files on disk, so the GUI asks to save first.

    previews: dict[str, tuple[float, str]] = {}

    @app.get("/api/templates")
    def templates() -> list[dict[str, Any]]:
        with session.lock:
            root = session.require().root
        try:
            return list_templates(root)
        except RenderError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/preview")
    def preview(body: dict[str, str]) -> dict[str, str]:
        with session.lock:
            root = session.require().root
        try:
            html = preview_html(root, body.get("model") or None, body.get("template", ""))
        except RenderError as exc:
            raise HTTPException(422, str(exc)) from exc
        now = time.monotonic()
        for key in [k for k, (t, _) in previews.items() if now - t > 60]:
            del previews[key]
        ticket = secrets.token_urlsafe(32)
        previews[ticket] = (now, html)
        return {"url": f"/preview/{ticket}"}

    @app.get("/preview/{ticket}", include_in_schema=False)
    def preview_page(ticket: str) -> Response:
        """Single-use, short-lived URL for the sandboxed preview iframe (no scripts)."""
        entry = previews.pop(ticket, None)
        if entry is None or time.monotonic() - entry[0] > 60:
            raise HTTPException(404)
        return Response(
            entry[1],
            media_type="text/html",
            headers={"Content-Security-Policy": PREVIEW_CSP},
        )

    @app.post("/api/build")
    def build(body: dict[str, str]) -> dict[str, Any]:
        with session.lock:
            root = session.require().root
            if session.dirty:
                raise HTTPException(409, "save your changes before building documents")
        fmt = body.get("format") or None
        if fmt is not None and fmt not in OUT_FORMATS:
            raise HTTPException(422, f"format: {', '.join(OUT_FORMATS)}")
        try:
            written = build_documents(
                root,
                body.get("model") or None,
                body.get("template") or None,
                fmt,
            )
        except RenderError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"written": [p.relative_to(root).as_posix() for p in written]}

    @app.post("/api/open-build-folder")
    def open_build_folder() -> dict[str, str]:
        """Open <project>/build in the file manager of the local machine."""
        local_only()
        with session.lock:
            folder = session.require().root.resolve() / "build"
        folder.mkdir(exist_ok=True)
        # a symlinked or non-directory "build" from a cloned repo could point at an app or
        # executable, which the opener would launch instead of showing a folder
        if folder.is_symlink() or not folder.is_dir():
            raise HTTPException(409, "build is not a plain folder")
        if sys.platform == "win32":
            os.startfile(folder)  # noqa: S606
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.Popen([opener, str(folder)])  # noqa: S603, S607
        return {"folder": str(folder)}

    # --- CI templates (ADR-0009) ----------------------------------------------------

    @app.get("/api/ci/{kind}")
    def ci_template(kind: str, image: str | None = None) -> dict[str, Any]:
        if kind not in ("gitlab", "github"):
            raise HTTPException(404, "unknown CI kind")
        with session.lock:
            root = session.require().root
        try:
            text = render_ci(root, kind, image)  # type: ignore[arg-type]
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        target = ci_target_path(root, kind)  # type: ignore[arg-type]
        return {"text": text, "target": str(target), "exists": target.exists()}

    @app.post("/api/ci/{kind}/write")
    def ci_write(kind: str, body: dict[str, Any]) -> dict[str, Any]:
        """Write the pipeline file; only on explicit user action, never overwrites silently."""
        data = ci_template(kind, body.get("image"))
        target = Path(data["target"])
        if target.exists() and not body.get("overwrite"):
            raise HTTPException(409, f"{target} exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data["text"], encoding="utf-8", newline="\n")
        return {"written": str(target)}

    # --- session actions ------------------------------------------------------------

    @app.post("/api/save")
    def save() -> dict[str, Any]:
        with session.lock:
            return {"written": session.save()}

    @app.post("/api/autosave")
    def autosave() -> dict[str, Any]:
        with session.lock:
            entry = session.autosave()
            return {"saved": entry is not None, "time": entry.time if entry else None}

    @app.get("/api/history")
    def history_list() -> dict[str, Any]:
        with session.lock:
            root = session.require().root
            return {
                "entries": [asdict(e) for e in history.entries(root)],
                "pending": session.pending,
            }

    @app.post("/api/history/{entry_id}/restore")
    def history_restore(entry_id: str) -> dict[str, Any]:
        if not history.ENTRY_ID.match(entry_id):
            raise HTTPException(404, "unknown version")
        with session.lock:
            project = session.require()
            try:
                models = history.restore(project.root, entry_id)
            except KeyError as exc:
                raise HTTPException(404, "unknown version") from exc
            except (OSError, ValueError) as exc:  # damaged file or schema mismatch
                raise HTTPException(422, f"version cannot be restored: {exc}") from exc
            session.checkpoint()  # undoable; files change only on the next save
            project.models = models
            session.pending = None
            return project_info()

    @app.post("/api/history/dismiss")
    def history_dismiss() -> dict[str, bool]:
        with session.lock:
            session.pending = None
            return {"ok": True}

    @app.post("/api/undo")
    def undo() -> dict[str, Any]:
        return _step(session, session.undo, session.redo)

    @app.post("/api/redo")
    def redo() -> dict[str, Any]:
        return _step(session, session.redo, session.undo)

    @app.get("/api/validate")
    def run_validation() -> list[dict[str, Any]]:
        with session.lock:
            project = session.require()
            return [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "file": relative(i, project.root),
                    "model": i.model,
                    "object": i.object_id,
                    "location": i.location,
                    "message": i.message,
                }
                for i in validate(project)
            ]

    @app.get("/api/changes")
    def external_changes() -> dict[str, Any]:
        with session.lock:
            project = session.require()
            now = _snapshot(project.root)
            changed = sorted(
                p for p in set(now) | set(session.files) if now.get(p) != session.files.get(p)
            )
            return {"changed": changed, "dirty": session.dirty}

    @app.post("/api/reload")
    def reload() -> dict[str, Any]:
        with session.lock:
            session.open(session.require().root)
            return project_info()

    # --- frontend ---------------------------------------------------------------------

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> Response:
        if path.startswith("api/"):
            raise HTTPException(404)
        # boundary first (string check): never even probe files outside the bundled frontend
        web = os.path.abspath(WEB_DIR)
        target = os.path.normpath(os.path.join(web, path))
        if path and target.startswith(web + os.sep) and os.path.isfile(target):
            return FileResponse(target)
        index = WEB_DIR / "index.html"
        if not index.exists():
            return Response("frontend not built: run `npm run build` in app/", status_code=503)
        return FileResponse(index)

    return app


def _max_risks(evaluations: dict[str, Any], sub: SubModel) -> dict[str, int]:
    """Highest risk of non-rejected threats per targeted element or flow."""
    out: dict[str, int] = {}
    for tid, ev in evaluations.items():
        t = sub.objects["threats"].get(tid)
        risk = ev["assessment"]["risk"]
        if not isinstance(t, Threat) or t.status == "rejected" or risk is None:
            continue
        for target in t.targets:
            out[target] = max(out.get(target, 0), risk)
    return out


def _evaluation(
    method: Method, t: Threat, assets: dict[str, Asset], project: Project
) -> dict[str, Any]:
    ev = evaluate(method, t, project.config)
    res = evaluate(method, t, project.config, residual=True) if t.residual else None
    sug = suggest_impact(method, t, assets)
    return {
        "assessment": ev.__dict__,
        "residual": res.__dict__ if res else None,
        "suggestion": sug.__dict__ if sug else None,
    }


def _step(
    session: Session, source: list[dict[str, SubModel]], target: list[dict[str, SubModel]]
) -> dict[str, Any]:
    with session.lock:
        project = session.require()
        if not source:
            raise HTTPException(409, "nothing to undo/redo")
        target.append({k: _copy_model(v) for k, v in project.models.items()})
        project.models = source.pop()
        session.changed()
        return {"ok": True}


def serve(
    project: Path | None,
    open_browser: bool = True,
    host: str = "127.0.0.1",
    port: int = 0,
    allowed_hosts: tuple[str, ...] = (),
    workspace: Path | None = None,
    auth: str | None = None,
    users_file: Path | None = None,
) -> None:
    """Start the GUI server; default a random free localhost port.

    `auth`: "basic" or "none"; default basic as soon as the GUI is reachable by others
    (secure by default), none for the local 127.0.0.1 GUI.
    """
    import socket
    import webbrowser

    import uvicorn

    # reachable by others (bound beyond loopback, or behind a proxy): server mode
    shared = bool(allowed_hosts) or host not in ("127.0.0.1", "::1", "localhost")
    auth = auth or ("basic" if shared else "none")
    # server mode works in a workspace folder holding any number of projects
    root = (workspace or Path.cwd()).resolve() if shared else None
    if root is not None and project is not None and not project.resolve().is_relative_to(root):
        raise SystemExit(f"--project must be inside the workspace {root}")
    users = None
    if auth == "basic":
        try:
            users, password_file = users_from(users_file, os.environ, root or Path.cwd())
        except (OSError, ValueError) as exc:
            raise SystemExit(f"error: {exc}") from exc
        if password_file:  # the password itself never goes to the log
            print(f"login: user '{next(iter(users))}', password in {password_file}", flush=True)
            print("  (set THREATWRIGHT_PASSWORD or --users-file for your own)", flush=True)
    elif shared:
        print("WARNING: --auth none: anyone who reaches this port can read and change", flush=True)
        print("  the models. Put a login in front (reverse proxy with authentication).", flush=True)
    sock = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET)
    sock.bind((host, port))
    port = sock.getsockname()[1]
    app = create_app(port, project, frozenset(allowed_hosts), root, users)
    shown = allowed_hosts[0] if allowed_hosts else "127.0.0.1"
    url = f"http://{shown}:{port}/"
    print(f"{PRODUCT_NAME} {__version__} running at {url} (Ctrl+C to stop)", flush=True)
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    config = uvicorn.Config(app, log_level="warning", server_header=False)
    uvicorn.Server(config).run(sockets=[sock])
