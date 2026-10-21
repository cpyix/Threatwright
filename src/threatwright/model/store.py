"""Load and save a project folder.

Saving merges each object into the YAML document it was loaded from, so
comments and formatting survive, and a file is only written when its content
actually changed: saving without edits never produces a diff.
"""

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scalarstring import LiteralScalarString, ScalarString

from threatwright.branding import PROJECT_FILE
from threatwright.model.migrations import upgrade
from threatwright.model.objects import (
    COLLECTIONS,
    CustomFields,
    DiagramLayout,
    ModelMeta,
    ModelObject,
    ProjectConfig,
)

MAX_FILE_BYTES = 1 << 20
MAX_DEPTH = 32
MAX_NODES = 50_000  # also stops alias bombs: shared nodes are counted per visit

CUSTOM_FIELDS_FILE = "custom-fields.yaml"
MODEL_FILE = "model.yaml"
LAYOUT_FILE = "diagram.layout.yaml"
DEFAULT_PREFIXES = {
    "elements": "E",
    "flows": "F",
    "assets": "A",
    "threats": "T",
    "measures": "M",
    "questions": "Q",
}
ALWAYS_WRITTEN = ("schema_version", "id", "uuid")


@dataclass(frozen=True)
class Issue:
    """A load or validation finding, addressable down to the field."""

    path: Path | None
    location: str
    message: str
    code: str = "schema"
    severity: Literal["error", "warning"] = "error"
    model: str | None = None
    object_id: str | None = None

    def __str__(self) -> str:
        loc = f" [{self.location}]" if self.location else ""
        return f"{self.severity}: {self.path}{loc}: {self.message} ({self.code})"


class LoadError(Exception):
    pass


@dataclass
class SubModel:
    name: str
    meta: ModelMeta
    layout: DiagramLayout = field(default_factory=DiagramLayout)
    objects: dict[str, dict[str, ModelObject]] = field(
        default_factory=lambda: {name: {} for name in COLLECTIONS}
    )

    def next_id(self, collection: str) -> str:
        prefix = self.meta.id_prefixes.get(collection, DEFAULT_PREFIXES[collection])
        used = [
            int(i.rsplit("-", 1)[1])
            for i in self.objects[collection]
            if i.rsplit("-", 1)[0] == prefix
        ]
        return f"{prefix}-{max(used, default=0) + 1:04d}"


# --- YAML I/O ------------------------------------------------------------------


def _yaml() -> YAML:
    # Round-trip mode only builds plain containers and scalars: no arbitrary objects.
    y = YAML(typ="rt")
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def read_yaml(path: Path) -> CommentedMap:
    data = path.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        raise LoadError(f"file larger than {MAX_FILE_BYTES} bytes")
    try:
        doc = _yaml().load(data.decode("utf-8-sig"))
    except (YAMLError, UnicodeDecodeError) as exc:
        raise LoadError(f"invalid YAML: {exc}") from exc
    if doc is None:  # empty or comments only
        doc = CommentedMap()
    if not isinstance(doc, CommentedMap):
        raise LoadError("top level must be a mapping")
    return doc


def write_yaml(path: Path, doc: CommentedMap) -> None:
    buf = io.StringIO()
    _yaml().dump(doc, buf)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")


def to_plain(node: Any) -> Any:
    """Copy a loaded document into plain Python types, enforcing depth/size limits."""
    count = 0

    def walk(n: Any, depth: int) -> Any:
        nonlocal count
        count += 1
        if depth > MAX_DEPTH or count > MAX_NODES:
            raise LoadError("document too deeply nested or too large")
        if isinstance(n, dict):
            return {str(k): walk(v, depth + 1) for k, v in n.items()}
        if isinstance(n, list):
            return [walk(v, depth + 1) for v in n]
        if isinstance(n, str):
            return str(n)
        return n

    return walk(node, 0)


# --- merge ---------------------------------------------------------------------


def _to_yaml(value: Any) -> Any:
    """Build a new YAML node in canonical style."""
    if isinstance(value, dict):
        m = CommentedMap()
        for k, v in value.items():
            m[k] = _to_yaml(v)
        return m
    if isinstance(value, list):
        s = CommentedSeq(_to_yaml(v) for v in value)
        if not any(isinstance(v, dict | list) for v in value):
            s.fa.set_flow_style()
        return s
    if isinstance(value, str) and "\n" in value:
        return LiteralScalarString(value)
    return value


def _replace(cur: Any, value: Any) -> Any:
    if isinstance(cur, ScalarString) and isinstance(value, str):
        return type(cur)(value)  # keep the author's string style
    return _to_yaml(value)


def _merge_seq(target: CommentedSeq, full: list[Any], minimal: list[Any] | None) -> bool:
    changed = False
    for i, value in enumerate(full):
        mini = minimal[i] if minimal and i < len(minimal) else value
        if i >= len(target):
            target.append(_to_yaml(mini))
            changed = True
        elif isinstance(value, dict) and isinstance(target[i], CommentedMap):
            changed |= _merge_map(target[i], value, mini if isinstance(mini, dict) else {})
        elif target[i] != value:
            target[i] = _replace(target[i], mini)
            changed = True
    while len(target) > len(full):
        del target[-1]
        changed = True
    return changed


def _merge_map(target: CommentedMap, full: dict[str, Any], minimal: dict[str, Any]) -> bool:
    """Update `target` in place to represent `full`; return whether anything changed.

    Keys absent from the file are only added when they differ from the default
    (i.e. appear in `minimal`), so files stay as short as their authors wrote them.
    """
    changed = False
    for key in [k for k in target if k not in full]:
        del target[key]
        changed = True
    order = {k: i for i, k in enumerate(full)}
    for key, value in full.items():
        mini = minimal.get(key, value)
        if key in target:
            cur = target[key]
            if isinstance(value, dict) and isinstance(cur, CommentedMap):
                changed |= _merge_map(cur, value, mini if isinstance(mini, dict) else {})
            elif isinstance(value, list) and isinstance(cur, CommentedSeq):
                changed |= _merge_seq(cur, value, mini if isinstance(mini, list) else None)
            elif cur != value:
                target[key] = _replace(cur, mini)
                changed = True
        elif key in minimal:
            pos = sum(1 for k in target if order[k] < order[key])
            target.insert(pos, key, _to_yaml(mini))
            changed = True
    return changed


def merge_into(doc: CommentedMap, obj: BaseModel) -> bool:
    full = obj.model_dump()
    minimal = obj.model_dump(exclude_defaults=True)
    for key in ALWAYS_WRITTEN:
        if key in full:
            minimal[key] = full[key]
    return _merge_map(doc, full, minimal)


# --- project -------------------------------------------------------------------


@dataclass
class Project:
    root: Path
    config: ProjectConfig
    custom_fields: CustomFields = field(default_factory=CustomFields)
    models: dict[str, SubModel] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    _docs: dict[Path, CommentedMap] = field(default_factory=dict, repr=False)
    _loaded_objects: set[Path] = field(default_factory=set, repr=False)
    migrated: list[Path] = field(default_factory=list)  # upgraded in memory, written on save

    @classmethod
    def load(cls, root: Path) -> "Project":
        root = Path(root)
        project = cls(root=root, config=ProjectConfig(name=root.name))
        config = project._load(root / PROJECT_FILE, ProjectConfig)
        if config is None:
            raise LoadError(f"not a project: {root / PROJECT_FILE} missing or invalid")
        project.config = config
        if (root / CUSTOM_FIELDS_FILE).exists():
            custom = project._load(root / CUSTOM_FIELDS_FILE, CustomFields)
            project.custom_fields = custom or project.custom_fields
        models_dir = root / "models"
        for model_dir in sorted(p for p in models_dir.glob("*") if p.is_dir()):
            meta = project._load(model_dir / MODEL_FILE, ModelMeta)
            if meta is None:
                continue
            sub = SubModel(model_dir.name, meta)
            layout_path = model_dir / LAYOUT_FILE
            if layout_path.exists():
                sub.layout = project._load(layout_path, DiagramLayout) or sub.layout
            for collection, obj_type in COLLECTIONS.items():
                for path in sorted((model_dir / collection).glob("*.yaml")):
                    obj = project._load(path, obj_type)
                    if obj is None:
                        continue
                    if obj.id != path.stem:
                        project.issues.append(
                            Issue(path, "id", f"id '{obj.id}' does not match file name")
                        )
                        continue
                    sub.objects[collection][obj.id] = obj
                    project._loaded_objects.add(path)
            project.models[sub.name] = sub
        return project

    def _load[T: BaseModel](self, path: Path, obj_type: type[T]) -> T | None:
        if not path.exists():
            self.issues.append(Issue(path, "", "file missing"))
            return None
        try:
            doc = read_yaml(path)
            if upgrade(obj_type.__name__, doc):  # older release: migrate in memory (ADR-0015)
                self.migrated.append(path)
            obj = obj_type.model_validate(to_plain(doc))
        except LoadError as exc:
            self.issues.append(Issue(path, "", str(exc)))
            return None
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(p) for p in err["loc"])
                self.issues.append(Issue(path, loc, err["msg"]))
            return None
        except ValueError as exc:  # newer or invalid schema_version (after: ValidationError is one)
            self.issues.append(Issue(path, "schema_version", str(exc)))
            return None
        self._docs[path] = doc
        return obj

    def move_document(self, model: str, collection: str, old_id: str, new_id: str) -> None:
        """Keep comments of a renamed object: its YAML document moves to the new file."""
        base = self.root / "models" / model / collection
        doc = self._docs.pop(base / f"{old_id}.yaml", None)
        if doc is not None:
            self._docs[base / f"{new_id}.yaml"] = doc

    def _save_one(self, path: Path, obj: BaseModel, written: list[Path]) -> None:
        doc = self._docs.setdefault(path, CommentedMap())
        if merge_into(doc, obj) or not path.exists() or path in self.migrated:
            write_yaml(path, doc)
            written.append(path)

    def save(self) -> list[Path]:
        """Write every changed file and delete files of removed objects."""
        written: list[Path] = []
        self._save_one(self.root / PROJECT_FILE, self.config, written)
        custom_path = self.root / CUSTOM_FIELDS_FILE
        if custom_path.exists() or self.custom_fields.fields:
            self._save_one(custom_path, self.custom_fields, written)
        wanted: set[Path] = set()
        for name, sub in self.models.items():
            model_dir = self.root / "models" / name
            self._save_one(model_dir / MODEL_FILE, sub.meta, written)
            layout_path = model_dir / LAYOUT_FILE
            if layout_path.exists() or sub.layout.nodes or sub.layout.edges or sub.layout.notes:
                self._save_one(layout_path, sub.layout, written)
            for collection, objects in sub.objects.items():
                for obj_id, obj in objects.items():
                    path = model_dir / collection / f"{obj_id}.yaml"
                    wanted.add(path)
                    self._save_one(path, obj, written)
        for path in self._loaded_objects - wanted:
            path.unlink(missing_ok=True)
            self._docs.pop(path, None)
            written.append(path)
        self._loaded_objects = wanted
        self.migrated.clear()
        return written
