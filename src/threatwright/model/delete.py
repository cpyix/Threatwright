"""Delete an element or data flow together with what hangs on it.

Flows of a deleted element always go (they cannot exist without both ends). Threats
that only target deleted objects, and measures only those threats use, go on request;
otherwise they stay and just lose the reference.
"""

from threatwright.model.objects import Flow, Question, Threat
from threatwright.model.store import SubModel


def deletion_plan(sub: SubModel, collection: str, obj_id: str) -> dict[str, list[str]]:
    """IDs that deleting `obj_id` removes: flows always, threats and measures with cascade."""
    if obj_id not in sub.objects[collection]:
        raise KeyError(obj_id)
    flows: list[str] = []
    if collection == "elements":
        flows = [
            f.id
            for f in sub.objects["flows"].values()
            if isinstance(f, Flow) and obj_id in (f.source, f.target)
        ]
    gone = {obj_id, *flows}
    threats = [t for t in _threats(sub) if t.targets and set(t.targets) <= gone]
    threat_ids = {t.id for t in threats}
    used_elsewhere = {m for t in _threats(sub) if t.id not in threat_ids for m in t.measures}
    measures = [
        m
        for m in dict.fromkeys(m for t in threats for m in t.measures)
        if m not in used_elsewhere and m in sub.objects["measures"]
    ]
    return {"flows": flows, "threats": sorted(threat_ids), "measures": measures}


def delete_with_refs(sub: SubModel, collection: str, obj_id: str, cascade: bool) -> None:
    """Delete `obj_id` (an element or flow) per `deletion_plan`; no dangling references remain."""
    plan = deletion_plan(sub, collection, obj_id)
    del sub.objects[collection][obj_id]
    sub.layout.nodes.pop(obj_id, None)
    for f in plan["flows"]:
        del sub.objects["flows"][f]
    gone = {obj_id, *plan["flows"]}
    removed_threats = set(plan["threats"]) if cascade else set()
    removed_measures = set(plan["measures"]) if cascade else set()
    for tid in removed_threats:
        del sub.objects["threats"][tid]
    for mid in removed_measures:
        del sub.objects["measures"][mid]
    for t in _threats(sub):
        t.targets = [x for x in t.targets if x not in gone]
        t.measures = [x for x in t.measures if x not in removed_measures]
    for q in sub.objects["questions"].values():
        if isinstance(q, Question):
            q.threats = [x for x in q.threats if x not in removed_threats]


def _threats(sub: SubModel) -> list[Threat]:
    return [t for t in sub.objects["threats"].values() if isinstance(t, Threat)]
