"""Where elements run and which trust boundaries a flow crosses.

`runs_on` places a process (or a virtual device) on a device of the same model;
`privilege` gives it a rights context on that host; `refines` links an element
to the element of another model it details (sub-model). Rules, reports and the
diagram all ask these questions here. app/src/topology.ts mirrors `boundary`.
"""

from typing import Literal

from threatwright.model.objects import Element, Flow, Threat
from threatwright.model.store import Project, SubModel

Boundary = Literal["zone", "privilege"]
PRIVILEGE_RANK = {"user": 0, "service": 1, "root": 2, "kernel": 3}


def _elements(sub: SubModel) -> dict[str, Element]:
    return {i: e for i, e in sub.objects["elements"].items() if isinstance(e, Element)}


def host_chain(sub: SubModel, el: Element) -> list[Element]:
    """Hosts of `el`, nearest first; stops at a missing host or a cycle."""
    elements = _elements(sub)
    chain: list[Element] = []
    seen = {el.id}
    current = el
    while current.runs_on and current.runs_on not in seen and current.runs_on in elements:
        current = elements[current.runs_on]
        seen.add(current.id)
        chain.append(current)
    return chain


def runs_on_cycle(sub: SubModel, el: Element) -> bool:
    chain = host_chain(sub, el)
    last = chain[-1] if chain else el
    return last.runs_on is not None and last.runs_on in {el.id, *(h.id for h in chain)}


def effective_zone(sub: SubModel, el: Element) -> str | None:
    """Own zone, else the zone of the nearest host that has one."""
    return next((e.zone for e in (el, *host_chain(sub, el)) if e.zone), None)


def context(el: Element) -> tuple[str, str, str | None] | None:
    """Rights context on the host: (host, level, account); None without host or privilege."""
    if el.runs_on is None or el.privilege is None:
        return None
    return el.runs_on, el.privilege.level, el.privilege.account


def boundary(sub: SubModel, flow: Flow) -> Boundary | None:
    elements = _elements(sub)
    src, tgt = elements.get(flow.source), elements.get(flow.target)
    if src is None or tgt is None:
        return None
    if effective_zone(sub, src) != effective_zone(sub, tgt):
        return "zone"
    a, b = context(src), context(tgt)
    if a and b and a[0] == b[0] and a != b:
        return "privilege"
    return None


def more_privileged(a: Element, b: Element) -> Element:
    rank = {e.id: PRIVILEGE_RANK[e.privilege.level] if e.privilege else -1 for e in (a, b)}
    return a if rank[a.id] >= rank[b.id] else b


def hosted(sub: SubModel, device_id: str) -> list[Element]:
    """Everything running on `device_id`, directly or through a virtual device."""
    return [e for e in _elements(sub).values() if device_id in {h.id for h in host_chain(sub, e)}]


def handled_assets(sub: SubModel, el_id: str) -> list[str]:
    """Assets an element handles: on its flows and on threats targeting it."""
    flows = [f for f in sub.objects["flows"].values() if isinstance(f, Flow)]
    threats = [t for t in sub.objects["threats"].values() if isinstance(t, Threat)]
    out = [a for f in flows if el_id in (f.source, f.target) for a in f.assets]
    out += [a for t in threats if el_id in t.targets for a in t.assets]
    return list(dict.fromkeys(out))


def split_ref(ref: str) -> tuple[str, str]:
    model, obj_id = ref.split("/", 1)
    return model, obj_id


def resolve_refines(project: Project, ref: str) -> Element | None:
    model, obj_id = split_ref(ref)
    sub = project.models.get(model)
    el = sub.objects["elements"].get(obj_id) if sub else None
    return el if isinstance(el, Element) else None


def parent_models(sub: SubModel) -> set[str]:
    """Models whose elements this model refines."""
    return {split_ref(e.refines)[0] for e in _elements(sub).values() if e.refines}


def parent_model(project: Project, sub: SubModel) -> str | None:
    """The one model this sub-model refines (None: not a sub-model or ambiguous)."""
    parents = parent_models(sub) - {sub.name}
    return next(iter(parents)) if len(parents) == 1 and parents <= set(project.models) else None


def submodels(project: Project, name: str) -> list[SubModel]:
    return [s for s in project.models.values() if parent_model(project, s) == name]


def refined_by(project: Project, model: str, el_id: str) -> list[tuple[SubModel, Element]]:
    """Elements of other models that refine `model/el_id`."""
    ref = f"{model}/{el_id}"
    return [
        (s, e) for s in project.models.values() for e in _elements(s).values() if e.refines == ref
    ]
