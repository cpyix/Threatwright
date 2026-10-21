"""Pydantic models for every file type of a project (schema version 1).

Enumerations whose values come from the method (interface, access, user,
asset classes) are plain strings here and are checked against the method
configuration by the rules engine, so a method change needs no schema change.
"""

import datetime
import uuid as uuidlib
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

SCHEMA_VERSION: Literal[1] = 1

Uuid = Annotated[uuidlib.UUID, PlainSerializer(str, return_type=str)]
ObjectId = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*-[0-9]{4,}$")]
Stride = Literal["S", "T", "R", "I", "D", "E"]


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
    libraries: list[str] = []
    templates: list[str] = []


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


class DiagramLayout(Versioned):
    """Content of diagram.layout.yaml: positions and canvas notes, never model content."""

    nodes: dict[str, NodeLayout] = {}
    notes: dict[str, DiagramNote] = {}


# --- per-object files --------------------------------------------------------


class Element(ModelObject):
    kind: Literal["process", "device", "datastore", "external"]
    zone: str | None = None
    configurations: list[str] = []
    stride_not_relevant: dict[Stride, str] = {}  # category -> rationale


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
