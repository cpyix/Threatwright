"""Template packages: template.yaml, lookup (project overrides bundled) and listing."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from threatwright.model.objects import Strict
from threatwright.model.store import Project, read_yaml, to_plain

BUILTIN_TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
TEMPLATE_FILE = "template.yaml"
TEMPLATE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
MAX_TEMPLATE_BYTES = 20 << 20

Format = Literal["docx", "odt", "md", "html"]
FORMATS: tuple[Format, ...] = ("docx", "odt", "md", "html")
FILE_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]*")  # no paths: stays in the package

SectionType = Literal[
    "cover",
    "scope",
    "method",
    "assets",
    "elements_and_flows",
    "threats",
    "rejected",
    "measures",
    "traceability",
    "questions",
    "risk_distribution",
    "changelog",
    "custom_fields",
    "text",
    "decisions",
    "signatures",
    "acceptance_impact",
    "approvals",
    "cra_requirements",
    "vulnerabilities",
]

# Selectable table columns per section type; the first list is the default.
COLUMNS: dict[str, tuple[list[str], list[str]]] = {
    "assets": (
        ["id", "title", "asset_class", "c", "i", "a"],
        ["id", "title", "asset_class", "c", "i", "a", "protects", "configurations", "description"],
    ),
    "elements": (
        ["id", "title", "kind", "zone", "configurations"],
        [
            "id",
            "title",
            "kind",
            "zone",
            "host",
            "privilege",
            "refines",
            "configurations",
            "description",
        ],
    ),
    "flows": (
        ["id", "title", "source", "target", "protocol", "assets"],
        [
            "id",
            "title",
            "source",
            "target",
            "protocol",
            "boundary",
            "assets",
            "configurations",
            "description",
        ],
    ),
    "attack_surface": (
        ["element", "listens_on", "authentication", "memory_safe", "sbom_ref"],
        ["element", "listens_on", "authentication", "memory_safe", "sbom_ref"],
    ),
    "threats": (
        ["id", "title", "stride", "targets", "risk", "treatment", "measures", "status"],
        [
            "id",
            "title",
            "stride",
            "targets",
            "exposure",
            "impact",
            "risk",
            "treatment",
            "measures",
            "residual_risk",
            "cra_refs",
            "status",
        ],
    ),
    "rejected": (
        ["id", "title", "rationale", "by"],
        ["id", "title", "stride", "targets", "rationale", "by"],
    ),
    "measures": (
        ["id", "title", "status", "owner", "evidence", "threats"],
        ["id", "title", "kind", "status", "owner", "due", "evidence", "threats", "cra_refs"],
    ),
    "traceability": (
        ["threat", "measure", "measure_status", "cra"],
        ["threat", "risk", "measure", "measure_status", "cra"],
    ),
    "questions": (
        ["id", "title", "addressee", "status", "answer"],
        ["id", "title", "addressee", "status", "answer", "threats"],
    ),
    "risk_distribution": (
        ["level", "label", "count", "treatment"],
        ["level", "label", "count", "treatment"],
    ),
    "changelog": (
        ["version", "date", "summary", "author"],
        ["model", "version", "date", "summary", "author"],
    ),
    "custom_fields": (["object", "field", "value"], ["object", "field", "value"]),
    "approvals": (
        ["threat", "status", "by", "role", "date", "rationale"],
        ["threat", "status", "risk", "by", "role", "date", "rationale", "model"],
    ),
    "cra_requirements": (
        ["id", "title", "status", "threats", "measures", "rationale"],
        ["id", "tr_id", "title", "status", "threats", "measures", "rationale", "model"],
    ),
    "vulnerabilities": (
        ["vulnerability", "element", "component", "state", "threats"],
        ["vulnerability", "element", "component", "state", "threats", "detail", "sources", "model"],
    ),
}


class I18nText(Strict):
    de: str
    en: str


class Section(Strict):
    type: SectionType
    enabled: bool = True
    title: str | I18nText | None = None
    columns: list[str] | None = None
    flow_columns: list[str] | None = None  # elements_and_flows only
    details: bool = True  # threats: one block per threat after the table
    text: str | I18nText | None = None  # text: Jinja, rendered against the context
    roles: list[str] = []  # signatures: one row per role

    @model_validator(mode="after")
    def _check(self) -> "Section":
        table = "elements" if self.type == "elements_and_flows" else self.type
        for cols, key in ((self.columns, table), (self.flow_columns, "flows")):
            if cols is None:
                continue
            allowed = COLUMNS.get(key, ([], []))[1]
            unknown = [c for c in cols if c not in allowed]
            if unknown:
                raise ValueError(f"unknown column(s) {unknown} for {key}; allowed: {allowed}")
        if self.type == "text" and self.text is None:
            raise ValueError("section type 'text' needs `text`")
        return self


class TemplateMeta(Strict):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=TEMPLATE_ID.pattern)
    name: I18nText
    description: I18nText | None = None
    format: Format | None = None
    file: str | None = None
    files: dict[Format, str] = {}  # several formats sharing one outline
    language: Literal["de", "en"] | None = None  # None: project language
    scope: Literal["model", "project"] = "model"
    outline: list[Section] = Field(min_length=1)

    @property
    def all_files(self) -> dict[Format, str]:
        single: dict[Format, str] = {self.format: self.file} if self.format and self.file else {}
        return {**single, **self.files}

    @model_validator(mode="after")
    def _files(self) -> "TemplateMeta":
        if bool(self.format) != bool(self.file):
            raise ValueError("`format` and `file` must be set together")
        if not self.all_files:
            raise ValueError("set `format` and `file`, or `files: {format: file}`")
        for name in self.all_files.values():
            if not FILE_NAME.fullmatch(name):
                raise ValueError(f"file '{name}' must be a plain file name in the package")
        return self


@dataclass(frozen=True)
class TemplatePackage:
    meta: TemplateMeta
    path: Path
    origin: Literal["bundled", "project"]

    def file(self, fmt: Format) -> Path:
        return self.path / self.meta.all_files[fmt]


class TemplateError(Exception):
    pass


def load_package(path: Path, origin: Literal["bundled", "project"] = "project") -> TemplatePackage:
    try:
        meta = TemplateMeta.model_validate(to_plain(read_yaml(path / TEMPLATE_FILE)))
    except Exception as exc:  # LoadError, ValidationError
        raise TemplateError(f"{path / TEMPLATE_FILE}: {exc}") from exc
    if meta.id != path.name:
        raise TemplateError(f"{path / TEMPLATE_FILE}: id '{meta.id}' must equal the folder name")
    for name in meta.all_files.values():
        f = path / name
        if not f.is_file():
            raise TemplateError(f"{f}: file missing")
        if f.stat().st_size > MAX_TEMPLATE_BYTES:
            raise TemplateError(f"{f}: larger than {MAX_TEMPLATE_BYTES} bytes")
    return TemplatePackage(meta, path, origin)


def _dirs(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    return sorted(
        p
        for p in base.iterdir()
        if p.is_dir() and TEMPLATE_ID.match(p.name) and (p / TEMPLATE_FILE).exists()
    )


def available(project_root: Path | None) -> dict[str, TemplatePackage]:
    """All templates by id; a project template replaces a bundled one with the same id."""
    out = {p.name: load_package(p, "bundled") for p in _dirs(BUILTIN_TEMPLATES)}
    if project_root is not None:
        out.update({p.name: load_package(p, "project") for p in _dirs(project_root / "templates")})
    return out


def active(project: Project) -> list[TemplatePackage]:
    """Templates listed in threatwright.yaml; an empty list means all bundled ids."""
    pkgs = available(project.root)
    ids = project.config.templates or [
        i for i in sorted(pkgs) if (BUILTIN_TEMPLATES / i / TEMPLATE_FILE).exists()
    ]
    missing = [i for i in ids if i not in pkgs]
    if missing:
        raise TemplateError(f"template(s) not found: {', '.join(missing)}")
    return [pkgs[i] for i in ids]
