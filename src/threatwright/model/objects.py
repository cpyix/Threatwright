"""Pydantic models for every file type of a project (schema version 1).

Enumerations whose values come from the method (interface, access, user,
asset classes) are plain strings here and are checked against the method
configuration by the rules engine, so a method change needs no schema change.
"""

import datetime
import uuid as uuidlib
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

SCHEMA_VERSION: Literal[1] = 1

Uuid = Annotated[uuidlib.UUID, PlainSerializer(str, return_type=str)]
ObjectId = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*-[0-9]{4,}$")]
Stride = Literal["S", "T", "R", "I", "D", "E"]
EVIDENCE_DIR = "evidence"
EvidenceRef = Annotated[
    # every path segment starts with a word character: no "..", no absolute paths
    str, Field(pattern=r"^(https?://\S+|evidence(/\w[\w. -]*)+)$")
]
# plain file name in the project folder sbom/ (no paths)
SbomFile = Annotated[str, Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9._-]*\.json$")]


def new_uuid() -> uuidlib.UUID:
    return uuidlib.uuid4()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Versioned(Strict):
    schema_version: Literal[1] = SCHEMA_VERSION


class ModelObject(Versioned):
    """Common fields of every object stored as its own file."""

    id: ObjectId
    uuid: Uuid = Field(default_factory=new_uuid)
    title: str
    short_name: str | None = None
    description: str | None = None
    library_ref: str | None = None
    custom: dict[str, Any] = {}


# --- project and model metadata -------------------------------------------


class ProjectConfig(Versioned):
    name: str
    uuid: Uuid = Field(default_factory=new_uuid)
    method: str = "tr-03183-1"
    language: Literal["de", "en"] = "de"
    lifecycle: Literal["development", "post_market"] = "development"
    support_until: datetime.date | None = None  # end of the support period (CRA Art. 13(8))
    next_review: datetime.date | None = None  # when the threat model is reviewed next
    libraries: list[str] = []
    templates: list[str] = []
    archived: bool = False  # hidden from project lists until searched for


class CustomField(Strict):
    name: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
    label: dict[Literal["de", "en"], str] = {}
    type: Literal[
        "text", "longtext", "number", "date", "choice", "multichoice", "reference", "bool"
    ] = "text"
    required: bool = False
    default: Any = None
    options: list[str] = []
    help: dict[Literal["de", "en"], str] = {}


class CustomFields(Versioned):
    """Content of custom-fields.yaml: extra fields per object type."""

    fields: dict[str, list[CustomField]] = {}


class Environment(Strict):
    """Environment indicators; allowed values are defined by the method."""

    interface: str | None = None
    access: str | None = None
    user: str | None = None


class Configuration(Strict):
    """A product variant / configuration level (Ausbaustufe)."""

    id: str
    title: str
    description: str | None = None


class Zone(Strict):
    id: str
    title: str
    description: str | None = None
    environment: Environment = Environment()


class ChangelogEntry(Strict):
    version: str
    date: datetime.date
    summary: str
    author: str | None = None


class ModelMeta(Versioned):
    """Content of models/<name>/model.yaml."""

    title: str
    uuid: Uuid = Field(default_factory=new_uuid)
    description: str | None = None
    id_prefixes: dict[str, str] = {}
    configurations: list[Configuration] = []
    zones: list[Zone] = []
    changelog: list[ChangelogEntry] = []
    # CRA Annex I requirement id -> why it does not apply to this product
    cra_not_applicable: dict[str, str] = {}


class NodeLayout(Strict):
    x: float
    y: float
    width: float | None = None
    height: float | None = None


class DiagramNote(Strict):
    """Free text on the diagram canvas (annotation, not part of the threat model)."""

    x: float
    y: float
    text: str


Side = Literal["top", "right", "bottom", "left"]


class Point(Strict):
    x: float
    y: float


class EdgeLayout(Strict):
    """Route of one data flow: the node sides it attaches to and its bend points."""

    source_side: Side | None = None  # None: the side facing the other end
    target_side: Side | None = None
    points: list[Point] = []  # absolute canvas coordinates; empty: automatic route


class DiagramLayout(Versioned):
    """Content of diagram.layout.yaml: positions, routes and canvas notes, never model content."""

    nodes: dict[str, NodeLayout] = {}
    edges: dict[str, EdgeLayout] = {}  # flow id -> route
    notes: dict[str, DiagramNote] = {}


# --- per-object files --------------------------------------------------------


PrivilegeLevel = Literal["kernel", "root", "service", "user"]
Authentication = Literal["none", "password", "shared-secret", "key", "certificate", "unknown"]
# <model>/<object id>: an element of another model of the same project
RefinesRef = Annotated[
    str, Field(pattern=r"^[a-z0-9][a-z0-9._-]*/[A-Za-z][A-Za-z0-9_]*-[0-9]{4,}$")
]
# only meaningful for running software or hardware, not for data stores or external entities
HOST_FIELDS = ("runs_on", "privilege", "listens_on", "authentication", "memory_safe")


class Privilege(Strict):
    """Rights of a process; a different level or account on the same host is a trust boundary."""

    level: PrivilegeLevel
    account: str | None = None
    capabilities: list[str] = []  # documentation only (e.g. CAP_NET_ADMIN), no boundary


class Listener(Strict):
    protocol: Literal["tcp", "udp", "unix"]
    port: int | None = Field(default=None, ge=1, le=65535)
    path: str | None = None  # unix sockets
    interfaces: str = "all"  # all | loopback | interface name

    @model_validator(mode="after")
    def _address(self) -> "Listener":
        if self.protocol == "unix" and self.port is not None:
            raise ValueError("a unix socket has a path, not a port")
        if self.protocol != "unix" and (self.port is None or self.path is not None):
            raise ValueError(f"{self.protocol} needs a port and no path")
        return self


class SbomRef(Strict):
    """Identity of the software component (package URL and/or CPE), for later SBOM matching."""

    purl: str | None = None
    cpe: str | None = None


class Element(ModelObject):
    kind: Literal["process", "device", "datastore", "external"]
    zone: str | None = None  # unset: the zone of the host (runs_on)
    configurations: list[str] = []
    stride_not_relevant: dict[Stride, str] = {}  # category -> rationale
    sbom: list[SbomFile] = []  # CycloneDX files in sbom/ describing this element's software
    runs_on: ObjectId | None = None  # device of the same model this element runs on
    privilege: Privilege | None = None
    listens_on: list[Listener] = []
    authentication: Authentication | None = None
    memory_safe: bool | None = None
    sbom_ref: SbomRef | None = None
    refines: RefinesRef | None = None  # element of another model this one details

    @model_validator(mode="after")
    def _host_fields(self) -> "Element":
        if self.kind in ("datastore", "external"):
            used = [f for f in HOST_FIELDS if getattr(self, f) not in (None, [])]
            if used:
                raise ValueError(f"{', '.join(used)} only apply to processes and devices")
        if self.kind == "external" and self.sbom_ref is not None:
            raise ValueError("sbom_ref does not apply to external entities")
        return self


class Flow(ModelObject):
    source: ObjectId
    target: ObjectId
    protocol: str | None = None
    bidirectional: bool = False
    assets: list[ObjectId] = []
    configurations: list[str] = []
    stride_not_relevant: dict[Stride, str] = {}


class CiaAmplifier(Strict):
    """Deviation from the class base values; rationale is mandatory (rules)."""

    c: float | None = None
    i: float | None = None
    a: float | None = None
    rationale: str | None = None


class Asset(ModelObject):
    asset_class: str
    protects: list[ObjectId] = []  # security assets inherit C'/I'/A' from these
    amplifier: CiaAmplifier | None = None
    configurations: list[str] = []


class Assessment(Environment):
    impact: int | None = Field(default=None, ge=1, le=5)
    rationale: str | None = None


class Decision(Strict):
    """Acceptance or rejection of a threat: who, in which role, when and why."""

    by: str | None = None
    role: str | None = None
    date: datetime.date | None = None
    rationale: str


ThreatStatus = Literal["identified", "assessed", "treated", "accepted", "rejected"]


class Threat(ModelObject):
    stride: list[Stride] = []
    targets: list[ObjectId] = []
    assets: list[ObjectId] = []
    configurations: list[str] = []
    cyber_cause: bool | None = None
    scenario: str | None = None
    consequence: str | None = None
    safety_related: bool = False
    finding: bool = False
    assessment: Assessment = Assessment()
    residual: Assessment | None = None
    measures: list[ObjectId] = []
    questions: list[ObjectId] = []
    cra_refs: list[str] = []
    vulnerabilities: list[str] = []  # ids (CVE, GHSA, ...) this threat treats
    status: ThreatStatus = "identified"
    acceptance: Decision | None = None
    rejection: Decision | None = None


MeasureKind = Literal["technical", "organizational", "design", "user_information", "supply_chain"]
MeasureStatus = Literal["proposed", "decided", "in_progress", "implemented"]


class OscalRef(Strict):
    source: str
    uuid: Uuid | None = None
    control_id: str | None = None


class Measure(ModelObject):
    kind: MeasureKind | None = None
    compensating: bool = False
    owner: str | None = None
    status: MeasureStatus = "proposed"
    due: datetime.date | None = None
    evidence: str | None = None
    # https links or files in the project folder evidence/ (path relative to the project)
    evidence_refs: list[EvidenceRef] = []
    cra_refs: list[str] = []
    oscal_ref: OscalRef | None = None


class Question(ModelObject):
    addressee: str | None = None
    status: Literal["open", "answered"] = "open"
    answer: str | None = None
    threats: list[ObjectId] = []


# Folder name inside models/<name>/ -> object type, in document order.
COLLECTIONS: dict[str, type[ModelObject]] = {
    "elements": Element,
    "flows": Flow,
    "assets": Asset,
    "threats": Threat,
    "measures": Measure,
    "questions": Question,
}

FILE_TYPES: dict[str, type[Versioned]] = {
    "project": ProjectConfig,
    "custom-fields": CustomFields,
    "model": ModelMeta,
    "diagram-layout": DiagramLayout,
    **{name.removesuffix("s"): cls for name, cls in COLLECTIONS.items()},
}
