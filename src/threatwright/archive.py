"""Project folders to and from .zip: a local project onto a server and back (ADR-0013)."""

import io
import os
import shutil
import stat
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from threatwright.auth import STATE_DIR
from threatwright.branding import PROJECT_FILE
from threatwright.history import HISTORY_DIR
from threatwright.model.store import LoadError, read_yaml, write_yaml

MAX_UPLOAD = 50 << 20  # compressed size of an uploaded archive
MAX_UNPACKED = 200 << 20  # sum of the declared file sizes (zip bombs)
MAX_FILES = 5000
SKIP = {HISTORY_DIR, STATE_DIR}  # local version history and a generated login


class ArchiveError(ValueError):
    pass


def pack(root: Path) -> bytes:
    """Zip a project folder (without the local version history) under its folder name."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root)
            if rel.parts[0] in SKIP or path.is_symlink() or not path.is_file():
                continue
            zf.write(path, (Path(root.name) / rel).as_posix())
    return buf.getvalue()


def unpack(data: bytes, workspace: Path, folder: str) -> Path:
    """Extract the project contained in a zip into `workspace/folder` (new or empty).

    The project is the folder holding the topmost threatwright.yaml; everything
    outside it is ignored. Symlinks are skipped; neither the folder nor any path in
    the archive may leave the workspace. Returns the project folder.
    """
    root = os.path.realpath(workspace)
    base = os.path.realpath(os.path.join(root, folder))
    if not base.startswith(root + os.sep):  # checked here, before any use of the path
        raise ArchiveError("the folder must be inside the workspace")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ArchiveError("not a .zip file") from exc
    with zf:
        files = [i for i in zf.infolist() if not i.is_dir()]
        if len(files) > MAX_FILES:
            raise ArchiveError(f"more than {MAX_FILES} files")
        if sum(i.file_size for i in files) > MAX_UNPACKED:
            raise ArchiveError(f"more than {MAX_UNPACKED >> 20} MB unpacked")
        names = {i.filename: i.filename.replace("\\", "/") for i in files}
        configs = sorted(
            (n for n in names.values() if n.rsplit("/", 1)[-1] == PROJECT_FILE),
            key=lambda n: n.count("/"),
        )
        if not configs:
            raise ArchiveError(f"the archive contains no {PROJECT_FILE}")
        prefix = configs[0][: -len(PROJECT_FILE)]
        if os.path.isdir(base) and os.listdir(base):
            raise ArchiveError(f"folder '{os.path.basename(base)}' already exists on the server")
        for info in files:
            name = names[info.filename]
            if not name.startswith(prefix) or stat.S_ISLNK(info.external_attr >> 16):
                continue
            dest = os.path.normpath(os.path.join(base, name[len(prefix) :]))
            if not dest.startswith(base + os.sep):
                raise ArchiveError(f"unsafe path in the archive: {name}")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            # reads at most the declared size, so MAX_UNPACKED also bounds the output
            with zf.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
    return Path(base)


def describe(folder: Path) -> dict[str, Any]:
    """Name and archive flag from the project config; the folder name if it cannot be read."""
    doc: Mapping[str, Any]
    try:
        doc = read_yaml(folder / PROJECT_FILE)
    except (LoadError, OSError):
        doc = {}
    name = doc.get("name")
    return {"name": str(name) if name else folder.name, "archived": doc.get("archived") is True}


def set_archived(folder: Path, archived: bool) -> None:
    """Change only the archive flag in threatwright.yaml (comments and the rest stay)."""
    doc = read_yaml(folder / PROJECT_FILE)
    if archived:
        doc["archived"] = True
    else:
        doc.pop("archived", None)
    write_yaml(folder / PROJECT_FILE, doc)


def projects_in(root: Path) -> list[dict[str, Any]]:
    """Project folders in `root` and one level below, relative to `root`."""
    found = [p for p in [root, *root.glob("*"), *root.glob("*/*")] if (p / PROJECT_FILE).is_file()]
    return sorted(
        ({"path": p.relative_to(root).as_posix() or ".", **describe(p)} for p in found),
        key=lambda x: x["path"],
    )
