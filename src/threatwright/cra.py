"""Coverage of the CRA essential requirements (Annex I parts I and II) per model.

A requirement counts as addressed by a measure that references it in `cra_refs`,
or that belongs to a threat referencing it. Requirements that do not apply need
a rationale in `cra_not_applicable` of model.yaml (CRA Art. 13(4), Annex VII).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cache
from typing import Literal

from threatwright.library import load_catalog
from threatwright.model.objects import Measure, Threat
from threatwright.model.store import SubModel

Status = Literal["not_applicable", "implemented", "planned", "threats_only", "open"]
ANNEX_I = "AI-"


@dataclass
class Requirement:
    id: str
    tr_id: str | None
    title: dict[str, str]
    status: Status
    threats: list[str] = field(default_factory=list)
    measures: list[str] = field(default_factory=list)
    rationale: str | None = None  # why it does not apply


@cache  # bundled catalog, never changes at runtime
def annex_i() -> dict[str, dict[str, str]]:
    """Annex I requirements of the CRA catalog: id -> {tr_id, de, en}."""
    entries = load_catalog("cra").entries
    return {k: v for k, v in entries.items() if k.startswith(ANNEX_I) and isinstance(v, dict)}


def coverage(sub: SubModel, parts: Sequence[SubModel] = ()) -> list[Requirement]:
    """`parts`: sub-models refining `sub`, same product (one assessment); their ids get
    the model name as prefix (`software/T-0001`), ids are only unique within a model."""

    def key(m: SubModel, obj_id: str) -> str:
        return obj_id if m is sub else f"{m.name}/{obj_id}"

    threats: list[tuple[str, Threat, list[str]]] = []
    measures: dict[str, Measure] = {}
    for m in (sub, *parts):
        for i, t in m.objects["threats"].items():
            if isinstance(t, Threat):
                threats.append((key(m, i), t, [key(m, x) for x in t.measures]))
        measures |= {
            key(m, i): o for i, o in m.objects["measures"].items() if isinstance(o, Measure)
        }
    rows = []
    for req_id, entry in annex_i().items():
        hit = sorted(k for k, t, _ in threats if req_id in t.cra_refs and t.status != "rejected")
        via_threat = {m for k, _, ms in threats if k in hit for m in ms}
        ms = sorted(i for i, m in measures.items() if req_id in m.cra_refs or i in via_threat)
        rationale = sub.meta.cra_not_applicable.get(req_id)
        status: Status
        if rationale is not None:
            status = "not_applicable"
        elif any(measures[m].status == "implemented" for m in ms):
            status = "implemented"
        elif ms:
            status = "planned"
        elif hit:
            status = "threats_only"
        else:
            status = "open"
        title = {"de": entry.get("de", ""), "en": entry.get("en", "")}
        rows.append(Requirement(req_id, entry.get("tr_id"), title, status, hit, ms, rationale))
    return rows
