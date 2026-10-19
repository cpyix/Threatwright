"""Element, threat and measure libraries plus reference catalogs.

A library is a folder with library.yaml (manifest) and any number of YAML
files whose top level holds `elements:`, `threats:` and/or `measures:` lists.
Projects activate libraries by name; a later library overrides entries of an
earlier one with the same kind and id. Copied objects keep
`library_ref: lib:<library>/<kind>/<id>@<rev>` so changes can be detected.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError

from threatwright.model.objects import Environment, MeasureKind, OscalRef, Strict, Stride
from threatwright.model.store import Issue, LoadError, Project, read_yaml, to_plain

BUILTIN_LIBRARIES = Path(__file__).parent / "libraries"
CATALOGS = Path(__file__).parent / "catalogs"
LIBRARY_FILE = "library.yaml"
NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
REF = re.compile(r"^lib:([a-z0-9._-]+)/(element|threat|measure)/([a-z0-9._-]+)@(\d+)$")

Kind = Literal["element", "threat", "measure"]


class I18n(Strict):
    de: str
    en: str


EntryId = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")


class BaseEntry(Strict):
    id: str = EntryId
    rev: int = Field(default=1, ge=1)
    sources: list[str] = []
    # Provenance for entries imported from OSCAL (ADR-0006); oscal_extra keeps
    # content the library format cannot represent, so re-imports lose nothing.
    oscal_ref: OscalRef | None = None
    oscal_extra: dict[str, Any] = {}
    category: str | None = None


class LibAsset(Strict):
    title: I18n
    asset_class: str
    rationale: I18n | None = None


class ElementType(BaseEntry):
    name: I18n
    kind: Literal["process", "device", "datastore", "external", "flow"]
    icon: str | None = None
    description: I18n | None = None
    interfaces: list[str] = []
    assets: list[LibAsset] = []
    environment: Environment = Environment()
    properties: dict[str, bool | str | None] = {}


class ThreatTemplate(BaseEntry):
    stride: list[Stride] = Field(min_length=1)
    applies_to: list[str] = Field(min_length=1)
    title: I18n
    scenario: I18n
    consequence: I18n
    environment: Environment = Environment()
    impact: int | None = Field(default=None, ge=1, le=5)
    safety_related: bool = False
    cra_refs: list[str] = []
    attack_ics: list[str] = []
    emb3d: list[str] = []
    iec62443: list[str] = []
    measures: list[str] = []


class ControlRef(Strict):
    catalog_uuid: str
    control_id: str


class MeasureTemplate(BaseEntry):
    title: I18n
    description: I18n
    kind: MeasureKind
    compensating: bool = False
    evidence: I18n | None = None
    cra_refs: list[str] = []
    iec62443: list[str] = []
    controls: list[ControlRef] = []


class Manifest(Strict):
    schema_version: Literal[1] = 1
    id: str = EntryId
    version: str
    title: I18n
    license: str
    description: I18n | None = None
    attribution: list[str] = []


class Catalog(Strict):
    schema_version: Literal[1] = 1
    id: str
    title: str
    version: str
    source: str
    retrieved: str | None = None
    entries: dict[str, str | dict[str, str]]


@dataclass
class Libraries:
    """All active libraries merged; `origin` records which library won."""

    manifests: dict[str, Manifest] = field(default_factory=dict)
    elements: dict[str, ElementType] = field(default_factory=dict)
    threats: dict[str, ThreatTemplate] = field(default_factory=dict)
    measures: dict[str, MeasureTemplate] = field(default_factory=dict)
    origin: dict[tuple[Kind, str], str] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)

    def ref(self, kind: Kind, entry_id: str) -> str:
        rev = self._entries(kind)[entry_id].rev
        return f"lib:{self.origin[(kind, entry_id)]}/{kind}/{entry_id}@{rev}"

    def resolve(self, ref: str) -> tuple[Kind, BaseEntry, int] | None:
        """Entry for a library_ref plus the revision recorded in the ref."""
        m = REF.match(ref)
        if not m:
            return None
        kind: Kind = m[2]  # type: ignore[assignment]
        entry = self._entries(kind).get(m[3])
        return (kind, entry, int(m[4])) if entry else None

    def _entries(self, kind: Kind) -> dict[str, Any]:
        by_kind: dict[str, dict[str, Any]] = {
            "element": self.elements,
            "threat": self.threats,
            "measure": self.measures,
        }
        return by_kind[kind]


def load_catalog(name: str) -> Catalog:
    return Catalog.model_validate(to_plain(read_yaml(CATALOGS / f"{name}.yaml")))


def _library_dir(project_root: Path | None, name: str) -> Path | None:
    candidates = [BUILTIN_LIBRARIES / name]
    if project_root is not None:
        candidates.insert(0, project_root / "libraries" / name)
    return next((p for p in candidates if (p / LIBRARY_FILE).exists()), None)


def load_libraries(names: list[str], project_root: Path | None = None) -> Libraries:
    libs = Libraries()
    for name in names:
        if not NAME.match(name) or (folder := _library_dir(project_root, name)) is None:
            libs.issues.append(
                Issue(project_root, "libraries", f"library '{name}' not found", "library-invalid")
            )
            continue
        _load_one(libs, name, folder)
    _check_integrity(libs)
    return libs


def _load_one(libs: Libraries, name: str, folder: Path) -> None:
    def problem(path: Path, loc: str, msg: str) -> None:
        libs.issues.append(Issue(path, loc, msg, "library-invalid"))

    try:
        libs.manifests[name] = Manifest.model_validate(to_plain(read_yaml(folder / LIBRARY_FILE)))
    except (LoadError, ValidationError) as exc:
        problem(folder / LIBRARY_FILE, "", str(exc))
        return
    types: dict[str, tuple[Kind, type[BaseEntry]]] = {
        "elements": ("element", ElementType),
        "threats": ("threat", ThreatTemplate),
        "measures": ("measure", MeasureTemplate),
    }
    for path in sorted(folder.rglob("*.yaml")):
        if path.name == LIBRARY_FILE:
            continue
        try:
            doc = to_plain(read_yaml(path))
        except LoadError as exc:
            problem(path, "", str(exc))
            continue
        for key, items in doc.items():
            if key not in types or not isinstance(items, list):
                problem(path, key, "expected a list under elements, threats or measures")
                continue
            kind, cls = types[key]
            for n, item in enumerate(items):
                try:
                    entry = cls.model_validate(item)
                except ValidationError as exc:
                    for err in exc.errors():
                        loc = ".".join(str(p) for p in err["loc"])
                        problem(path, f"{key}.{n}.{loc}", err["msg"])
                    continue
                target = libs._entries(kind)
                if libs.origin.get((kind, entry.id)) == name:
                    problem(path, f"{key}.{n}.id", f"duplicate {kind} id '{entry.id}'")
                target[entry.id] = entry
                libs.origin[(kind, entry.id)] = name


def _check_integrity(libs: Libraries) -> None:
    catalogs = {c: set(load_catalog(c).entries) for c in ("cra", "attack-ics", "emb3d", "iec62443")}

    def bad(kind: Kind, entry_id: str, loc: str, values: list[str], valid: set[str]) -> None:
        for v in values:
            if v not in valid:
                lib = libs.origin[(kind, entry_id)]
                libs.issues.append(
                    Issue(
                        None,
                        f"{lib}/{kind}/{entry_id}.{loc}",
                        f"unknown reference '{v}'",
                        "library-invalid",
                    )
                )

    for t in libs.threats.values():
        bad("threat", t.id, "applies_to", t.applies_to, set(libs.elements))
        bad("threat", t.id, "measures", t.measures, set(libs.measures))
        bad("threat", t.id, "cra_refs", t.cra_refs, catalogs["cra"])
        bad("threat", t.id, "attack_ics", t.attack_ics, catalogs["attack-ics"])
        bad("threat", t.id, "emb3d", t.emb3d, catalogs["emb3d"])
        bad("threat", t.id, "iec62443", t.iec62443, catalogs["iec62443"])
    for m in libs.measures.values():
        bad("measure", m.id, "cra_refs", m.cra_refs, catalogs["cra"])
        bad("measure", m.id, "iec62443", m.iec62443, catalogs["iec62443"])


# --- project integration --------------------------------------------------------


@dataclass
class Outdated:
    model: str
    object_id: str
    ref: str
    current_rev: int
    title: str


def check_library_refs(project: Project, libs: Libraries) -> tuple[list[Issue], list[Outdated]]:
    """Warnings for unknown refs, plus the list of objects with a newer library entry."""
    issues: list[Issue] = []
    outdated: list[Outdated] = []
    for sub in project.models.values():
        for coll, objects in sub.objects.items():
            for obj in objects.values():
                if not obj.library_ref:
                    continue
                path = project.root / "models" / sub.name / coll / f"{obj.id}.yaml"
                found = libs.resolve(obj.library_ref)
                if found is None:
                    issues.append(
                        Issue(
                            path,
                            "library_ref",
                            f"'{obj.library_ref}' not found",
                            "library-ref-unknown",
                            "warning",
                            sub.name,
                            obj.id,
                        )
                    )
                    continue
                _, entry, rev = found
                if entry.rev > rev:
                    outdated.append(
                        Outdated(sub.name, obj.id, obj.library_ref, entry.rev, obj.title)
                    )
                    issues.append(
                        Issue(
                            path,
                            "library_ref",
                            f"library has a newer revision ({rev} -> {entry.rev})",
                            "library-outdated",
                            "warning",
                            sub.name,
                            obj.id,
                        )
                    )
    return issues, outdated
