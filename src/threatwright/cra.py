"""Coverage of the CRA essential requirements (Annex I parts I and II) per model.

A requirement counts as addressed by a measure that references it in `cra_refs`,
or that belongs to a threat referencing it. Requirements that do not apply need
a rationale in `cra_not_applicable` of model.yaml (CRA Art. 13(4), Annex VII).
"""

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


def coverage(sub: SubModel) -> list[Requirement]:
    threats = [t for t in sub.objects["threats"].values() if isinstance(t, Threat)]
    measures = {i: m for i, m in sub.objects["measures"].items() if isinstance(m, Measure)}
    rows = []
    for req_id, entry in annex_i().items():
        hit = sorted(t.id for t in threats if req_id in t.cra_refs and t.status != "rejected")
        via_threat = {m for t in threats if t.id in hit for m in t.measures}
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
