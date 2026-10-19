"""Build documents, preview, list, check and derive templates (CLI, server and GUI entry points)."""

import json
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Literal

from jinja2 import TemplateError as JinjaError
from jinja2 import TemplateSyntaxError, meta
from jinja2.sandbox import ImmutableSandboxedEnvironment

from threatwright.method import Method, load_method
from threatwright.model.store import Issue, Project
from threatwright.render import odt, pdf, word
from threatwright.render.context import KNOWN_VARIABLES, Ctx, build_context, filters_for
from threatwright.render.env import make_env, make_filters
from threatwright.render.package import (
    MAX_TEMPLATE_BYTES,
    TEMPLATE_FILE,
    TEMPLATE_ID,
    TemplateError,
    TemplatePackage,
    active,
    available,
    load_package,
)

OutFormat = Literal["docx", "odt", "md", "html", "pdf"]
OUT_FORMATS: tuple[OutFormat, ...] = ("docx", "odt", "md", "html", "pdf")


class RenderError(Exception):
    pass


def _fix_zip(path: Path) -> None:
    """Fixed timestamps so unchanged input gives byte-identical DOCX files."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(path) as zf:
        odt.rewrite_zip(tmp, zf, {})
    tmp.replace(path)


def _render(pkg: TemplatePackage, fmt: OutFormat, ctx: Ctx, method: Method, out: Path) -> None:
    filters = filters_for(method, ctx["lang"])
    try:
        if fmt == "pdf":
            source_fmt: Literal["docx", "odt"] = "docx" if "docx" in pkg.meta.all_files else "odt"
            with tempfile.TemporaryDirectory(prefix="tw-build-") as tmp:
                source = Path(tmp) / f"{out.stem}.{source_fmt}"
                _render(pkg, source_fmt, ctx, method, source)
                pdf.convert(source, out)
        elif fmt in ("md", "html"):
            env = make_env(filters, [pkg.path], autoescape=fmt == "html")
            text = env.get_template(pkg.meta.all_files[fmt]).render(ctx)
            out.write_text(text, encoding="utf-8", newline="\n")
        elif fmt == "docx":
            word.render_docx(pkg.file("docx"), ctx, make_env(filters, text=False), out)
            _fix_zip(out)
        else:
            odt.render_odt(pkg.file("odt"), ctx, make_env(filters), out)
    except JinjaError as exc:
        raise RenderError(f"{pkg.path.name}/{fmt}: {exc}") from exc
    except pdf.PdfError as exc:
        raise RenderError(str(exc)) from exc
    except (ValueError, KeyError, zipfile.BadZipFile) as exc:
        raise RenderError(f"{pkg.path.name}/{fmt}: {exc}") from exc


def _context(project: Project, method: Method, pkg: TemplatePackage, model: str | None) -> Ctx:
    try:
        return build_context(project, method, pkg.meta, model)
    except JinjaError as exc:  # free-text sections of the outline
        raise RenderError(f"{pkg.path.name}/template.yaml: {exc}") from exc


def _formats(pkg: TemplatePackage) -> list[OutFormat]:
    fmts: list[OutFormat] = [f for f in pkg.meta.all_files]
    return fmts + (["pdf"] if {"docx", "odt"} & set(fmts) else [])


def _load(project_root: Path) -> tuple[Project, Method]:
    project = Project.load(Path(project_root))
    return project, load_method(project.root, project.config)


def build_documents(
    project_root: Path,
    model: str | None = None,
    template: str | None = None,
    fmt: OutFormat | None = None,
    out_dir: Path | None = None,
) -> list[Path]:
    """Render templates for models; default: all active templates, all models, all
    formats of each template except PDF (PDF only when asked for)."""
    project, method = _load(project_root)
    out_dir = Path(out_dir) if out_dir else project.root / "build"
    if model is not None and model not in project.models:
        raise RenderError(f"model '{model}' not found")
    try:
        if template is not None:
            pkgs = available(project.root)
            if template not in pkgs:
                raise RenderError(f"template '{template}' not found")
            selected = [pkgs[template]]
        else:
            selected = active(project)
    except TemplateError as exc:
        raise RenderError(str(exc)) from exc
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for pkg in selected:
        fmts: list[OutFormat]
        if fmt is None:
            fmts = [f for f in _formats(pkg) if f != "pdf"]
        elif fmt in _formats(pkg):
            fmts = [fmt]
        elif template is not None:
            raise RenderError(f"template '{pkg.meta.id}' cannot produce {fmt}")
        else:
            continue
        if pkg.meta.scope == "project":
            targets: list[str | None] = [None]
        else:
            targets = [model] if model else list(sorted(project.models))
        for name in targets:
            ctx = _context(project, method, pkg, name)
            for f in fmts:
                stem = f"{name}-{pkg.meta.id}" if name else pkg.meta.id
                out = out_dir / f"{stem}.{f}"
                _render(pkg, f, ctx, method, out)
                written.append(out)
    return written


def preview_html(project_root: Path, model: str | None, template_id: str) -> str:
    """HTML of a template for the GUI; templates without HTML use the generic layout."""
    project, method = _load(project_root)
    try:
        pkg = available(project.root).get(template_id)
    except TemplateError as exc:
        raise RenderError(str(exc)) from exc
    if pkg is None:
        raise RenderError(f"template '{template_id}' not found")
    if pkg.meta.scope == "model":
        model = model or next(iter(sorted(project.models)), None)
        if model not in project.models:
            raise RenderError(f"model '{model}' not found")
    ctx = _context(project, method, pkg, model if pkg.meta.scope == "model" else None)
    env = make_env(filters_for(method, ctx["lang"]), [pkg.path], autoescape=True)
    name = pkg.meta.all_files.get("html", "document.html.j2")
    try:
        return env.get_template(name).render(ctx)
    except JinjaError as exc:
        raise RenderError(f"{pkg.path.name}/html: {exc}") from exc


def list_templates(project_root: Path | None = None) -> list[dict[str, Any]]:
    project = Project.load(Path(project_root)) if project_root else None
    pkgs = available(project.root if project else None)
    try:
        active_ids = {p.meta.id for p in active(project)} if project else set(pkgs)
    except TemplateError:
        active_ids = set(project.config.templates) if project else set()
    return [
        {
            "id": pkg.meta.id,
            "name": pkg.meta.name.model_dump(),
            "description": pkg.meta.description.model_dump() if pkg.meta.description else None,
            "formats": _formats(pkg),
            "scope": pkg.meta.scope,
            "language": pkg.meta.language,
            "origin": pkg.origin,
            "active": pkg.meta.id in active_ids,
            "path": str(pkg.path),
        }
        for pkg in pkgs.values()
    ]


# --- check ---------------------------------------------------------------------------


def _issue(path: Path, message: str, code: str, location: str = "") -> Issue:
    return Issue(path, location, message, code=code)


def _check_source(
    env: ImmutableSandboxedEnvironment, source: str, path: Path, location: str
) -> list[Issue]:
    allowed = KNOWN_VARIABLES | set(env.globals)
    try:
        ast = env.parse(source)
        env.compile(source)  # unknown filters
    except TemplateSyntaxError as exc:
        return [_issue(path, exc.message or str(exc), "template-syntax", f"line {exc.lineno}")]
    except JinjaError as exc:
        return [_issue(path, str(exc), "template-syntax", location)]
    issues = [
        _issue(path, f"unknown variable '{name}'", "template-variable", location)
        for name in sorted(meta.find_undeclared_variables(ast) - allowed)
    ]
    for ref in meta.find_referenced_templates(ast):
        if ref is not None and env.loader is not None:
            try:
                env.loader.get_source(env, ref)
            except JinjaError:
                issues.append(_issue(path, f"template '{ref}' not found", "template-syntax"))
    return issues


def check_template(path: Path) -> list[Issue]:
    """Validate template.yaml, syntax and variables of every template file."""
    path = Path(path)
    folder = path.parent if path.name == TEMPLATE_FILE else path
    try:
        pkg = load_package(folder)
    except TemplateError as exc:
        return [_issue(folder / TEMPLATE_FILE, str(exc), "template-yaml")]
    filters = make_filters("de", {}, {})
    issues: list[Issue] = []
    for i, section in enumerate(pkg.meta.outline):
        texts = (
            [section.text]
            if isinstance(section.text, str)
            else ([section.text.de, section.text.en] if section.text else [])
        )
        for text in texts:
            issues += _check_source(
                make_env(filters), text, folder / TEMPLATE_FILE, f"outline[{i}].text"
            )
    for fmt, name in pkg.meta.all_files.items():
        file = folder / name
        try:
            if fmt in ("md", "html"):
                env = make_env(filters, [folder])
                source = file.read_text(encoding="utf-8")
                issues += _check_source(env, source, file, "")
                continue
            env = make_env(filters, text=fmt != "docx")
            names = word.undeclared(file, env) if fmt == "docx" else odt.undeclared(file, env)
            allowed = KNOWN_VARIABLES | set(env.globals)
            issues += [
                _issue(file, f"unknown variable '{n}'", "template-variable")
                for n in sorted(names - allowed)
            ]
        except TemplateSyntaxError as exc:
            issues.append(_issue(file, exc.message or str(exc), "template-syntax"))
        except (JinjaError, ValueError, KeyError, OSError, zipfile.BadZipFile) as exc:
            issues.append(_issue(file, str(exc), "template-syntax"))
    return issues


# --- derive ---------------------------------------------------------------------------

DEFAULT_OUTLINE = """\
  - type: cover
  - type: scope
  - type: method
  - type: assets
  - type: elements_and_flows
  - type: risk_distribution
  - type: threats
  - type: rejected
  - type: measures
  - type: traceability
  - type: questions
  - type: changelog
"""


def derive_template(
    existing_doc: Path, out_dir: Path, fmt: Literal["docx", "odt"] | None = None
) -> Path:
    """Turn an existing .docx/.odt into a template package in `out_dir` (its folder name
    becomes the template id). Styles, header/footer and page setup are kept; the body
    is replaced by the standard outline. Returns the path of template.yaml."""
    existing_doc, out_dir = Path(existing_doc), Path(out_dir)
    suffix = existing_doc.suffix.lower().lstrip(".")
    fmt = fmt or (suffix if suffix in ("docx", "odt") else None)  # type: ignore[assignment]
    if fmt not in ("docx", "odt"):
        raise RenderError("derive needs a .docx or .odt document")
    if existing_doc.stat().st_size > MAX_TEMPLATE_BYTES:
        raise RenderError(f"{existing_doc}: larger than {MAX_TEMPLATE_BYTES} bytes")
    template_id = re.sub(r"[^a-z0-9._-]+", "-", out_dir.name.lower()).strip("-.")
    if not TEMPLATE_ID.match(template_id) or template_id != out_dir.name:
        raise RenderError(f"folder name '{out_dir.name}' is not a valid template id")
    meta_path = out_dir / TEMPLATE_FILE
    if meta_path.exists():
        raise RenderError(f"{meta_path} already exists")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"template.{fmt}"
    try:
        if fmt == "docx":
            word.derive(existing_doc, target)
            _fix_zip(target)
        else:
            odt.derive(existing_doc, target)
    except (ValueError, KeyError, zipfile.BadZipFile) as exc:
        raise RenderError(f"{existing_doc}: {exc}") from exc
    de = json.dumps(f"Abgeleitet aus {existing_doc.name}", ensure_ascii=False)
    en = json.dumps(f"Derived from {existing_doc.name}", ensure_ascii=False)
    meta_path.write_text(
        f"schema_version: 1\n"
        f"id: {template_id}\n"
        f"name:\n  de: {template_id}\n  en: {template_id}\n"
        f"description:\n  de: {de}\n  en: {en}\n"
        f"format: {fmt}\n"
        f"file: template.{fmt}\n"
        f"outline:\n{DEFAULT_OUTLINE}",
        encoding="utf-8",
        newline="\n",
    )
    return meta_path
