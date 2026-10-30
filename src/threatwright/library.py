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

from threatwright.model.objects import (
    Authentication,
    Environment,
    Listener,
    MeasureKind,
    OscalRef,
    Privilege,
    Strict,
    Stride,
)
from threatwright.model.store import Issue, LoadError, Project, read_yaml, to_plain

BUILTIN_LIBRARIES = Path(__file__).parent / "libraries"
CATALOGS = Path(__file__).parent / "catalogs"
CATALOG_NAMES = ("cra", "attack-ics", "emb3d", "iec62443", "etsi-303645", "asvs", "masvs")
# catalog id -> field name on threat/measure templates ("cra" is checked via cra_refs)
CATALOG_FIELDS = {
    "attack-ics": "attack_ics",
    "emb3d": "emb3d",
    "iec62443": "iec62443",
    "etsi-303645": "etsi303645",
    "asvs": "asvs",
    "masvs": "masvs",
}
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
    # defaults for new elements of this type (processes and devices)
    privilege: Privilege | None = None
    authentication: Authentication | None = None
    listens_on: list[Listener] = []


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
    etsi303645: list[str] = []
    asvs: list[str] = []
    masvs: list[str] = []
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
    etsi303645: list[str] = []
    asvs: list[str] = []
    masvs: list[str] = []
    controls: list[ControlRef] = []


class Manifest(Strict):
    schema_version: Literal[1] = 1
    id: str = EntryId
    version: str
    title: I18n
    license: str
    description: I18n | None = None
    attribution: list[str] = []
    requires: list[str] = []  # libraries that must be active before this one (measures, types)


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


_CACHE: dict[tuple[Any, ...], Libraries] = {}


def _fingerprint(folder: Path) -> tuple[tuple[str, int, int], ...]:
    stats = ((p, p.stat()) for p in folder.rglob("*.yaml"))
    return tuple(sorted((str(p), s.st_mtime_ns, s.st_size) for p, s in stats))


def load_libraries(names: list[str], project_root: Path | None = None) -> Libraries:
    """Libraries by name; project libraries (libraries/<name>/) win over bundled ones.

    Parsing the YAML takes seconds for a large library and validation needs it on
    every call, so results are cached until a file of the library changes.
    """
    folders = [(n, _library_dir(project_root, n) if NAME.match(n) else None) for n in names]
    key = (
        str(project_root),
        tuple((n, str(f)) for n, f in folders),
        tuple(_fingerprint(f) for _, f in folders if f is not None),
    )
    cached = _CACHE.get(key)
    if cached is None:
        cached = Libraries()
        for name, folder in folders:
            if folder is None:
                cached.issues.append(
                    Issue(
                        project_root, "libraries", f"library '{name}' not found", "library-invalid"
                    )
                )
                continue
            _load_one(cached, name, folder)
        _check_requires(cached, names, project_root)
        _check_integrity(cached)
        if len(_CACHE) > 16:  # ponytail: tiny cache, cleared wholesale
            _CACHE.clear()
        _CACHE[key] = cached
    # own containers per caller; the entries themselves are never modified
    return Libraries(
        dict(cached.manifests),
        dict(cached.elements),
        dict(cached.threats),
        dict(cached.measures),
        dict(cached.origin),
        list(cached.issues),
    )


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


def _check_requires(libs: Libraries, names: list[str], project_root: Path | None) -> None:
    for name, manifest in libs.manifests.items():
        for req in manifest.requires:
            if req not in names[: names.index(name)]:
                libs.issues.append(
                    Issue(
                        project_root,
                        "libraries",
                        f"library '{name}' needs '{req}' listed before it",
                        "library-invalid",
                    )
                )


def _check_integrity(libs: Libraries) -> None:
    catalogs = {c: set(load_catalog(c).entries) for c in CATALOG_NAMES}

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
        for cat, attr in CATALOG_FIELDS.items():
            bad("threat", t.id, attr, getattr(t, attr), catalogs[cat])
    for m in libs.measures.values():
        bad("measure", m.id, "cra_refs", m.cra_refs, catalogs["cra"])
        for cat, attr in CATALOG_FIELDS.items():
            if attr in MeasureTemplate.model_fields:
                bad("measure", m.id, attr, getattr(m, attr), catalogs[cat])


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
