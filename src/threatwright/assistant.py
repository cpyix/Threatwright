"""Turn library entries into model objects; STRIDE suggestions and coverage.

Environment of an adopted threat: the interface comes from the threat template
(it describes the attack path); access and user come from the zone of the
target where set, otherwise from the template. Measures suggested by the
template are reused when the model already contains them (same library entry).
"""

from dataclasses import dataclass, field
from typing import Literal

from threatwright.library import REF, ElementType, Libraries, MeasureTemplate, ThreatTemplate
from threatwright.method import Method
from threatwright.model.objects import (
    Assessment,
    Asset,
    Element,
    Environment,
    Flow,
    Measure,
    ModelObject,
    NodeLayout,
    ProjectConfig,
    Threat,
)
from threatwright.model.store import SubModel

Lang = Literal["de", "en"]


def _lang(config: ProjectConfig) -> Lang:
    return config.language


def library_type(obj: ModelObject) -> str | None:
    """Element type id an element or flow was created from."""
    m = REF.match(obj.library_ref or "")
    return m[3] if m and m[2] == "element" else None


def _entry_id(obj: ModelObject, kind: str) -> str | None:
    m = REF.match(obj.library_ref or "")
    return m[3] if m and m[2] == kind else None


def _zone_env(sub: SubModel, target: ModelObject) -> Environment:
    element = target
    if isinstance(target, Flow):
        element = sub.objects["elements"].get(target.target, target)
    zone_id = element.zone if isinstance(element, Element) else None
    zone = next((z for z in sub.meta.zones if z.id == zone_id), None)
    return zone.environment if zone else Environment()


def _new_assets(
    sub: SubModel, libs: Libraries, etype: ElementType, owner_title: str, lang: Lang
) -> list[str]:
    ids = []
    for a in etype.assets:
        asset_id = sub.next_id("assets")
        sub.objects["assets"][asset_id] = Asset(
            id=asset_id,
            title=f"{getattr(a.title, lang)} ({owner_title})",
            asset_class=a.asset_class,
            description=getattr(a.rationale, lang) if a.rationale else None,
        )
        ids.append(asset_id)
    return ids


def add_element(
    sub: SubModel,
    libs: Libraries,
    config: ProjectConfig,
    type_id: str,
    title: str | None = None,
    zone: str | None = None,
    position: tuple[float, float] | None = None,
) -> Element:
    """New element from a library element type, with its typical assets."""
    etype = libs.elements[type_id]
    if etype.kind == "flow":
        raise ValueError(f"'{type_id}' is a data flow type")
    lang = _lang(config)
    element = Element(
        id=sub.next_id("elements"),
        title=title or getattr(etype.name, lang),
        kind=etype.kind,
        zone=zone,
        library_ref=libs.ref("element", type_id),
        description=getattr(etype.description, lang) if etype.description else None,
    )
    sub.objects["elements"][element.id] = element
    _new_assets(sub, libs, etype, element.title, lang)
    if position is not None:
        sub.layout.nodes[element.id] = NodeLayout(x=position[0], y=position[1])
    return element


def add_flow(
    sub: SubModel,
    libs: Libraries,
    config: ProjectConfig,
    source: str,
    target: str,
    type_id: str | None = None,
) -> Flow:
    """New data flow between two elements, optionally typed by a library flow type."""
    for end in (source, target):
        if end not in sub.objects["elements"]:
            raise KeyError(end)
    lang = _lang(config)
    etype = libs.elements.get(type_id) if type_id else None
    if etype is not None and etype.kind != "flow":
        raise ValueError(f"'{type_id}' is not a data flow type")
    names = [sub.objects["elements"][e].title for e in (source, target)]
    title = getattr(etype.name, lang) if etype else f"{names[0]} → {names[1]}"
    flow_id = sub.next_id("flows")
    assets = _new_assets(sub, libs, etype, f"{flow_id}", lang) if etype else []
    flow = Flow(
        id=flow_id,
        title=title,
        source=source,
        target=target,
        protocol=etype.name.en if etype else None,
        assets=assets,
        library_ref=libs.ref("element", type_id) if etype and type_id else None,
    )
    sub.objects["flows"][flow.id] = flow
    return flow


def _measure_for(sub: SubModel, libs: Libraries, template: MeasureTemplate, lang: Lang) -> str:
    for m in sub.objects["measures"].values():
        if _entry_id(m, "measure") == template.id:
            return m.id
    measure = Measure(
        id=sub.next_id("measures"),
        title=getattr(template.title, lang),
        description=getattr(template.description, lang),
        kind=template.kind,
        compensating=template.compensating,
        evidence=getattr(template.evidence, lang) if template.evidence else None,
        cra_refs=list(template.cra_refs),
        library_ref=libs.ref("measure", template.id),
    )
    sub.objects["measures"][measure.id] = measure
    return measure.id


def adopt_threat(
    sub: SubModel, libs: Libraries, config: ProjectConfig, template_id: str, target_id: str
) -> Threat:
    """New threat on a target from a library template incl. suggested measures."""
    template: ThreatTemplate = libs.threats[template_id]
    target = sub.objects["elements"].get(target_id) or sub.objects["flows"].get(target_id)
    if target is None:
        raise KeyError(target_id)
    lang = _lang(config)

    def fill(text: str) -> str:
        return text.replace("{element}", target.title)

    zone = _zone_env(sub, target)
    env = template.environment
    measures = [
        _measure_for(sub, libs, libs.measures[m], lang)
        for m in template.measures
        if m in libs.measures
    ]
    threat = Threat(
        id=sub.next_id("threats"),
        title=fill(getattr(template.title, lang)),
        stride=list(template.stride),
        targets=[target_id],
        assets=list(target.assets) if isinstance(target, Flow) else [],
        configurations=list(getattr(target, "configurations", [])),
        scenario=fill(getattr(template.scenario, lang)),
        consequence=fill(getattr(template.consequence, lang)),
        safety_related=template.safety_related,
        assessment=Assessment(
            interface=env.interface or zone.interface,
            access=zone.access or env.access,
            user=zone.user or env.user,
            impact=template.impact,
        ),
        measures=measures,
        cra_refs=list(template.cra_refs),
        library_ref=libs.ref("threat", template_id),
    )
    sub.objects["threats"][threat.id] = threat
    return threat


# --- suggestions and coverage -------------------------------------------------------


@dataclass
class Suggestion:
    template_id: str
    title: str
    scenario: str
    impact: int | None
    safety_related: bool
    adopted: bool


@dataclass
class Category:
    relevant: bool
    existing: list[str] = field(default_factory=list)
    not_relevant: str | None = None
    suggestions: list[Suggestion] = field(default_factory=list)


def _kind(obj: ModelObject) -> str:
    return obj.kind if isinstance(obj, Element) else "flow"


def suggestions(
    sub: SubModel, libs: Libraries, method: Method, config: ProjectConfig, target_id: str
) -> dict[str, Category]:
    """Per STRIDE category: existing threats and fitting library templates."""
    target = sub.objects["elements"].get(target_id) or sub.objects["flows"].get(target_id)
    if not isinstance(target, Element | Flow):
        raise KeyError(target_id)
    lang = _lang(config)
    kind = _kind(target)
    etype = library_type(target)
    if etype in libs.elements:
        types = {etype}
    elif kind == "flow":
        # flow templates are protocol specific (fieldbus, VPN, Wi-Fi); none fits an untyped flow
        types = set()
    else:  # no library type: offer templates for element types of the same kind
        types = {e.id for e in libs.elements.values() if e.kind == kind}
    threats = [t for t in sub.objects["threats"].values() if isinstance(t, Threat)]
    adopted = {(_entry_id(t, "threat"), tuple(t.targets)) for t in threats}
    relevant = set(method.stride_per_kind.map.get(kind, []))
    out: dict[str, Category] = {}
    for s in "STRIDE":
        cat = Category(
            relevant=s in relevant,
            existing=[t.id for t in threats if target_id in t.targets and s in t.stride],
            not_relevant=target.stride_not_relevant.get(s),  # type: ignore[call-overload]
        )
        for tpl in libs.threats.values():
            if s in tpl.stride and types & set(tpl.applies_to):
                cat.suggestions.append(
                    Suggestion(
                        template_id=tpl.id,
                        title=getattr(tpl.title, lang).replace("{element}", target.title),
                        scenario=getattr(tpl.scenario, lang).replace("{element}", target.title),
                        impact=tpl.impact,
                        safety_related=tpl.safety_related,
                        adopted=any(a == tpl.id and target_id in tg for a, tg in adopted),
                    )
                )
        out[s] = cat
    return out


@dataclass
class CoverageRow:
    id: str
    title: str
    kind: str
    cells: dict[str, Category]


def coverage(sub: SubModel, method: Method) -> list[CoverageRow]:
    """Elements and flows x STRIDE: threat count and 'not relevant' marks."""
    threats = [t for t in sub.objects["threats"].values() if isinstance(t, Threat)]
    rows = []
    for coll in ("elements", "flows"):
        for obj in sub.objects[coll].values():
            if not isinstance(obj, Element | Flow):
                continue
            kind = _kind(obj)
            relevant = set(method.stride_per_kind.map.get(kind, []))
            cells = {
                s: Category(
                    relevant=s in relevant,
                    existing=[t.id for t in threats if obj.id in t.targets and s in t.stride],
                    not_relevant=obj.stride_not_relevant.get(s),  # type: ignore[call-overload]
                )
                for s in "STRIDE"
            }
            rows.append(CoverageRow(obj.id, obj.title, kind, cells))
    return rows
