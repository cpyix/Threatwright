"""Autosave and version history of the open models (ADR-0014).

Snapshots live in <project>/.threatwright-history/, which ignores itself in Git:
the project files are still only written on an explicit save. A snapshot holds
every model of the project; restoring one replaces the models in the editor.
"""

import gzip
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from threatwright.model.migrations import upgrade
from threatwright.model.objects import COLLECTIONS, DiagramLayout, ModelMeta
from threatwright.model.store import SubModel

HISTORY_DIR = ".threatwright-history"
KEEP = 200  # ponytail: plain count limit; thin out old autosaves by age if folders get large
Kind = Literal["auto", "save", "open"]  # open: state on disk when an unsaved autosave was found
ENTRY_ID = re.compile(r"^\d{8}T\d{6}_\d{6}-(auto|save|open)$")


@dataclass(frozen=True)
class Entry:
    id: str
    time: str  # ISO 8601, UTC
    kind: Kind
    counts: dict[str, int]  # objects per collection over all models


def dump(models: dict[str, SubModel]) -> dict[str, Any]:
    return {
        name: {
            "meta": sub.meta.model_dump(mode="json"),
            "layout": sub.layout.model_dump(mode="json"),
            "objects": {
                c: {i: o.model_dump(mode="json") for i, o in objs.items()}
                for c, objs in sub.objects.items()
            },
        }
        for name, sub in models.items()
    }


def _valid[T: BaseModel](cls: type[T], doc: dict[str, Any]) -> T:
    upgrade(cls.__name__, doc)  # snapshots of an older release migrate like files (ADR-0015)
    return cls.model_validate(doc)


def load(data: dict[str, Any]) -> dict[str, SubModel]:
    return {
        name: SubModel(
            name,
            _valid(ModelMeta, m["meta"]),
            _valid(DiagramLayout, m["layout"]),
            {
                c: {i: _valid(cls, o) for i, o in m["objects"].get(c, {}).items()}
                for c, cls in COLLECTIONS.items()
            },
        )
        for name, m in data.items()
    }


def _dir(root: Path) -> Path:
    folder = root / HISTORY_DIR
    if not folder.exists():
        folder.mkdir()
        (folder / ".gitignore").write_text("*\n", encoding="utf-8")  # never committed
    return folder


def _counts(data: dict[str, Any]) -> dict[str, int]:
    return {c: sum(len(m["objects"].get(c, {})) for m in data.values()) for c in COLLECTIONS}


def record(root: Path, models: dict[str, SubModel], kind: Kind) -> Entry:
    now = datetime.now(UTC)
    entry_id = f"{now:%Y%m%dT%H%M%S_%f}-{kind}"
    data = dump(models)
    entry = Entry(entry_id, now.isoformat(), kind, _counts(data))
    payload = {"time": entry.time, "kind": kind, "counts": entry.counts, "models": data}
    folder = _dir(root)
    (folder / f"{entry_id}.json.gz").write_bytes(gzip.compress(json.dumps(payload).encode()))
    for old in sorted(folder.glob("*.json.gz"))[:-KEEP]:
        old.unlink()
    return entry


def _files(root: Path) -> dict[str, Path]:
    folder = root / HISTORY_DIR
    if not folder.is_dir():
        return {}
    found = {p.name.removesuffix(".json.gz"): p for p in folder.glob("*.json.gz")}
    return {k: p for k, p in found.items() if ENTRY_ID.match(k)}


def _read(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(gzip.decompress(path.read_bytes()))
    return data


def entries(root: Path) -> list[Entry]:
    """Newest first."""
    out = []
    for entry_id, path in sorted(_files(root).items(), reverse=True):
        try:
            p = _read(path)
            out.append(Entry(entry_id, p["time"], p["kind"], p["counts"]))
        except (OSError, ValueError, KeyError):
            continue  # a damaged snapshot must not hide the others
    return out


def restore(root: Path, entry_id: str) -> dict[str, SubModel]:
    """Models of a snapshot. Unknown ids raise KeyError (ids come from the listing only)."""
    return load(_read(_files(root)[entry_id])["models"])
