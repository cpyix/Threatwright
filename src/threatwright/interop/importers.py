"""Import threats from OWASP Threat Dragon (v2 JSON) and from CSV.

Imports only ever add objects (new ids via `SubModel.next_id`); existing
content is never changed. A model that does not exist yet is created.

Threat Dragon mapping (documented in docs/git-arbeitsweise.md):
actor -> external, process -> process, store -> datastore, flow -> Flow,
trust-boundary-box -> zone (elements whose centre lies inside), threats ->
Threat with status `identified` (the TR method needs its own assessment),
mitigation -> Measure (`implemented` if the threat was "Mitigated", else
`proposed`). Threat Dragon type/severity/status are kept in the description.
"""

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from threatwright.interop.export import FORMULA_START
from threatwright.model.objects import (
    Element,
    Flow,
    Measure,
    ModelMeta,
    NodeLayout,
    Stride,
    Threat,
    Zone,
)
from threatwright.model.store import LoadError, Project, SubModel

MAX_IMPORT_BYTES = 5 << 20
MAX_ROWS = 10_000
MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
STRIDE_WORDS: dict[str, Stride] = {
    "spoofing": "S",
    "tampering": "T",
    "repudiation": "R",
    "information disclosure": "I",
    "denial of service": "D",
    "elevation of privilege": "E",
    # Threat Dragon's CIA model
    "confidentiality": "I",
    "integrity": "T",
    "availability": "D",
}
TD_KINDS = {"actor": "external", "process": "process", "store": "datastore"}
TD_BOUNDARY_LINE = "trust-boundary-curve"
TD_BOUNDARY_BOX = "trust-boundary-box"
DIAGRAM_OFFSET = 2000.0  # diagrams are laid out side by side in one model
TRUE = {"1", "true", "yes", "ja", "x", "wahr"}
FALSE = {"", "0", "false", "no", "nein", "falsch"}
DECIDED = {"accepted", "rejected"}
THREAT_STATUS = {"identified", "assessed", "treated", "accepted", "rejected"}


class ImportFailed(Exception):
    pass


@dataclass
class ImportResult:
    model: str
    created_model: bool
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    written: list[Path] = field(default_factory=list)

    def count(self, key: str) -> None:
        self.counts[key] = self.counts.get(key, 0) + 1


def _read(file: Path) -> bytes:
    size = file.stat().st_size
    if size > MAX_IMPORT_BYTES:
        raise ImportFailed(f"{file.name}: larger than {MAX_IMPORT_BYTES} bytes")
    return file.read_bytes()


def _target(project_root: Path, model_name: str, title: str) -> tuple[Project, SubModel, bool]:
    if not MODEL_NAME.match(model_name):
        raise ImportFailed(f"invalid model name '{model_name}'")
    try:
        project = Project.load(project_root)
    except LoadError as exc:
        raise ImportFailed(str(exc)) from exc
    if project.issues:
        # A file that failed to load could be overwritten by a "new" id.
        raise ImportFailed(f"project has load errors, fix them first: {project.issues[0]}")
    sub = project.models.get(model_name)
    if sub is not None:
        return project, sub, False
    sub = SubModel(model_name, ModelMeta(title=title or model_name))
    project.models[model_name] = sub
    return project, sub, True


def _add[T: Element | Flow | Threat | Measure](
    sub: SubModel, collection: str, cls: type[T], **values: Any
) -> T:
    obj = cls(id=sub.next_id(collection), **values)
    sub.objects[collection][obj.id] = obj
    return obj


# --- Threat Dragon ---------------------------------------------------------------------


def _d(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _l(v: Any) -> list[Any]:
    return v if isinstance(v, list) else []


def _s(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ""


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


def _cell_name(cell: dict[str, Any]) -> str:
    attrs = _d(cell.get("attrs"))
    return (
        _s(_d(cell.get("data")).get("name"))
        or _s(_d(attrs.get("text")).get("text"))
        or _s(_d(attrs.get("label")).get("text"))
    )


def _stride(word: str) -> Stride | None:
    w = word.strip().lower()
    if len(w) == 1 and w.upper() in "STRIDE":
        return w.upper()  # type: ignore[return-value]
    return STRIDE_WORDS.get(w)


def _box(cell: dict[str, Any]) -> tuple[float, float, float, float] | None:
    pos, size = _d(cell.get("position")), _d(cell.get("size"))
    x, y, w, h = (
        _num(pos.get("x")),
        _num(pos.get("y")),
        _num(size.get("width")),
        _num(size.get("height")),
    )
    if x is None or y is None:
        return None
    return x, y, w or 0.0, h or 0.0


def import_threat_dragon(project_root: Path, file: Path, model_name: str) -> ImportResult:
    try:
        doc = json.loads(_read(file).decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ImportFailed(f"{file.name}: not a valid JSON file ({exc})") from exc
    detail = _d(_d(doc).get("detail"))
    diagrams = _l(detail.get("diagrams"))
    if not diagrams:
        raise ImportFailed(f"{file.name}: no Threat Dragon diagrams found (detail.diagrams)")
    if any("diagramJson" in _d(d) for d in diagrams):
        raise ImportFailed(f"{file.name}: Threat Dragon v1 format; open and save it in v2 first")

    title = _s(_d(doc.get("summary")).get("title"))
    project, sub, created = _target(project_root, model_name, title)
    result = ImportResult(model_name, created)
    warn = result.warnings.append
    zone_ids = {z.id for z in sub.meta.zones}
    ids: dict[tuple[int, str], str] = {}  # (diagram, cell id) -> element/flow id
    owners: list[tuple[str, dict[str, Any]]] = []  # (element/flow id, cell) with threats

    for n, diagram in enumerate(diagrams):
        cells = [_d(c) for c in _l(_d(diagram).get("cells"))]
        boxes: list[tuple[str, tuple[float, float, float, float]]] = []
        new_elements: list[tuple[Element, tuple[float, float, float, float] | None]] = []
        for cell in cells:
            shape, name = _s(cell.get("shape")), _cell_name(cell)
            data = _d(cell.get("data"))
            if shape in TD_KINDS:
                el = _add(
                    sub,
                    "elements",
                    Element,
                    title=name or shape,
                    description=_s(data.get("description")) or None,
                    kind=TD_KINDS[shape],
                )
                ids[(n, _s(cell.get("id")))] = el.id
                result.count("elements")
                box = _box(cell)
                if box:
                    x, y, w, h = box
                    sub.layout.nodes[el.id] = NodeLayout(
                        x=x + n * DIAGRAM_OFFSET, y=y, width=w or None, height=h or None
                    )
                new_elements.append((el, box))
                owners.append((el.id, cell))
                if data.get("outOfScope") is True:
                    warn(f"{el.id} '{el.title}': marked out of scope in Threat Dragon")
            elif shape == TD_BOUNDARY_BOX:
                box = _box(cell)
                if box is None:
                    warn(f"trust boundary '{name}' without position ignored")
                    continue
                i = len(zone_ids) + 1
                while f"Z-TB{i}" in zone_ids:
                    i += 1
                zone = Zone(id=f"Z-TB{i}", title=name or f"Trust boundary {i}")
                zone_ids.add(zone.id)
                sub.meta.zones.append(zone)
                boxes.append((zone.id, box))
                result.count("zones")
            elif shape == TD_BOUNDARY_LINE:
                warn(f"trust boundary line '{name}' cannot be mapped to a zone; set zones manually")
            elif shape != "flow" and shape:
                warn(f"shape '{shape}' ignored")
        for el, ebox in new_elements:
            if ebox is None:
                continue
            cx, cy = ebox[0] + ebox[2] / 2, ebox[1] + ebox[3] / 2
            inside = [
                (b[2] * b[3], zid)
                for zid, b in boxes
                if b[0] <= cx <= b[0] + b[2] and b[1] <= cy <= b[1] + b[3]
            ]
            if inside:
                el.zone = min(inside)[1]  # innermost box
        for cell in cells:
            if _s(cell.get("shape")) != "flow":
                continue
            name = _cell_name(cell) or "Data flow"
            src = ids.get((n, _s(_d(cell.get("source")).get("cell"))))
            dst = ids.get((n, _s(_d(cell.get("target")).get("cell"))))
            if src is None or dst is None:
                warn(f"data flow '{name}' is not connected to two elements; ignored")
                continue
            data = _d(cell.get("data"))
            flow = _add(
                sub,
                "flows",
                Flow,
                title=name,
                description=_s(data.get("description")) or None,
                source=src,
                target=dst,
                protocol=_s(data.get("protocol")) or None,
                bidirectional=data.get("isBidirectional") is True,
            )
            result.count("flows")
            owners.append((flow.id, cell))

    for target, cell in owners:
        for raw in _l(_d(cell.get("data")).get("threats")):
            _td_threat(sub, target, _d(raw), result)

    result.written = project.save()
    return result


def _td_threat(sub: SubModel, target: str, raw: dict[str, Any], result: ImportResult) -> None:
    td_type, status = _s(raw.get("type")), _s(raw.get("status"))
    stride = _stride(td_type)
    if td_type and stride is None:
        result.warnings.append(
            f"threat '{_s(raw.get('title'))}': type '{td_type}' has no STRIDE match"
        )
    info = ", ".join(
        f"{k} {v}"
        for k, v in (("type", td_type), ("severity", _s(raw.get("severity"))), ("status", status))
        if v
    )
    measures = []
    mitigation = _s(raw.get("mitigation"))
    if mitigation:
        m = _add(
            sub,
            "measures",
            Measure,
            title=mitigation.splitlines()[0][:120],
            description=mitigation,
            status="implemented" if status.lower() == "mitigated" else "proposed",
        )
        measures.append(m.id)
        result.count("measures")
    _add(
        sub,
        "threats",
        Threat,
        title=_s(raw.get("title")) or td_type or "Threat",
        description=f"Imported from Threat Dragon ({info})." if info else None,
        scenario=_s(raw.get("description")) or None,
        stride=[stride] if stride else [],
        targets=[target],
        measures=measures,
    )
    result.count("threats")


# --- CSV ----------------------------------------------------------------------------------


def _clean(value: str | None) -> str:
    v = (value or "").strip()
    if v.startswith("'") and v[1:2] and v[1] in "".join(FORMULA_START):
        v = v[1:]  # undo the export's formula-injection guard
    return v


def _split(value: str) -> list[str]:
    return [p.strip() for p in re.split(r"[,;]", value) if p.strip()]


def _bool(value: str) -> bool | None:
    v = value.lower()
    return True if v in TRUE else False if v in FALSE else None


def import_csv(project_root: Path, file: Path, model_name: str) -> ImportResult:
    """Threats from a CSV with the export's header names (`;` or `,`, BOM optional)."""
    try:
        text = _read(file).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportFailed(f"{file.name}: not UTF-8 ({exc})") from exc
    first = text.split("\n", 1)[0]
    delimiter = ";" if first.count(";") >= first.count(",") else ","
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter)
    header = [h.strip() for h in reader.fieldnames or []]
    if "title" not in header:
        raise ImportFailed(f"{file.name}: header row with a 'title' column expected")
    reader.fieldnames = header
    project, sub, created = _target(project_root, model_name, "")
    result = ImportResult(model_name, created)
    warn = result.warnings.append
    known = {c: set(sub.objects[c]) for c in sub.objects}
    targets_ok = known["elements"] | known["flows"]

    for line, row in enumerate(reader, start=2):
        if line > MAX_ROWS + 1:
            warn(f"more than {MAX_ROWS} rows; rest ignored")
            break
        col = {k: _clean(v) for k, v in row.items() if isinstance(k, str) and isinstance(v, str)}
        title = col.get("title", "")
        if not title:
            if any(col.values()):
                warn(f"line {line}: no title; skipped")
            continue

        def refs(
            name: str, valid: set[str], line: int = line, col: dict[str, str] = col
        ) -> list[str]:
            values = _split(col.get(name, ""))
            for v in values:
                if v not in valid:
                    warn(f"line {line}: {name} '{v}' does not exist in model '{model_name}'")
            return [v for v in values if v in valid]

        stride: list[Stride] = []
        for word in _split(col.get("stride", "")):
            s = _stride(word)
            if s is None:
                warn(f"line {line}: unknown STRIDE category '{word}'")
            elif s not in stride:
                stride.append(s)
        status = col.get("status", "") or "identified"
        if status not in THREAT_STATUS or status in DECIDED:
            warn(f"line {line}: status '{status}' imported as 'identified'")
            status = "identified"
        impact: int | None = None
        if col.get("impact"):
            try:
                impact = int(col["impact"])
            except ValueError:
                warn(f"line {line}: impact '{col['impact']}' is not a number")
        safety = _bool(col.get("safety_related", ""))
        if safety is None:
            warn(f"line {line}: safety_related '{col['safety_related']}' not understood")
        try:
            _add(
                sub,
                "threats",
                Threat,
                title=title,
                scenario=col.get("scenario") or None,
                stride=stride,
                targets=refs("targets", targets_ok),
                assets=refs("assets", known["assets"]),
                measures=refs("measures", known["measures"]),
                cra_refs=_split(col.get("cra_refs", "")),
                safety_related=bool(safety),
                status=status,
                assessment={
                    "interface": col.get("interface") or None,
                    "access": col.get("access") or None,
                    "user": col.get("user") or None,
                    "impact": impact,
                },
            )
        except ValidationError as exc:
            warn(f"line {line}: skipped ({exc.errors()[0]['loc']}: {exc.errors()[0]['msg']})")
            continue
        result.count("threats")

    result.written = project.save()
    return result
