"""Document context: plain data computed once from project, method and evaluations.

Nothing computed here is ever stored. Templates see only dicts, lists, strings,
numbers and dates (see docs/vorlagenreferenz.md for the data model).
"""

from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from threatwright import sbom, topology
from threatwright.branding import PRODUCT_NAME
from threatwright.cra import coverage as cra_coverage
from threatwright.library import load_catalog
from threatwright.method import (
    BUILTIN_METHODS,
    METHOD_FILE,
    Method,
    asset_impact,
    evaluate,
    risk,
)
from threatwright.model.objects import Asset, Element, Flow, Listener, ModelObject, Threat
from threatwright.model.store import Project, SubModel, read_yaml, to_plain
from threatwright.render.env import make_env, make_filters, sort_by_risk
from threatwright.render.labels import Lang, t
from threatwright.render.package import TemplateMeta
from threatwright.render.sections import build_outline
from threatwright.topology import effective_zone
from threatwright.vcs import revision

Ctx = dict[str, Any]
Filters = dict[str, Callable[..., Any]]

# Top-level template variables (documented in docs/vorlagenreferenz.md).
KNOWN_VARIABLES = frozenset(
    {
        "lang",
        "project",
        "model",
        "models",
        "document",
        "method",
        "assets",
        "elements",
        "flows",
        "threats",
        "rejected_threats",
        "measures",
        "questions",
        "changelog",
        "traceability",
        "risk_distribution",
        "unassessed_count",
        "custom_fields",
        "acceptance",
        "approvals",
        "revision",
        "cra_requirements",
        "vulnerabilities",
        "outline",
    }
)


def _i18n(label: Any, lang: Lang) -> str:
    return str(getattr(label, lang))


def _builtin_method(method: Method) -> Method:
    """The unmodified bundled method with the same id (the "TR default")."""
    path = BUILTIN_METHODS / method.id / METHOD_FILE
    if not path.exists():
        return method
    return Method.model_validate(to_plain(read_yaml(path)))


def _base(obj: ModelObject, sub: SubModel, prefix: str = "") -> Ctx:
    return {
        "id": prefix + obj.id,
        "uuid": str(obj.uuid),
        "title": obj.title,
        "short_name": obj.short_name,
        "description": obj.description,
        "library_ref": obj.library_ref,
        "custom": dict(obj.custom),
        "model": sub.name,
    }


def _titles(sub: SubModel) -> dict[str, str]:
    return {i: o.title for objs in sub.objects.values() for i, o in objs.items()}


def _refs(ids: list[str], titles: dict[str, str], prefix: str = "") -> list[Ctx]:
    return [{"id": prefix + i, "title": titles.get(i, "")} for i in ids]


def _privilege(el: Element, lang: Lang) -> str | None:
    p = el.privilege
    if p is None:
        return None
    return t(f"privilege.{p.level}", lang) + (f" ({p.account})" if p.account else "")


def _listener(x: Listener) -> str:
    where = x.path if x.protocol == "unix" else str(x.port)
    return f"{x.protocol}/{where} ({x.interfaces})"


def _topology(project: Project, sub: SubModel, el: Element, lang: Lang, prefix: str) -> Ctx:
    """runs_on, privilege context, refines and the technical attack surface of an element."""
    titles = _titles(sub)
    target = topology.resolve_refines(project, el.refines) if el.refines else None
    ref = el.sbom_ref
    return {
        "runs_on": prefix + el.runs_on if el.runs_on else None,
        "runs_on_title": titles.get(el.runs_on or "", ""),
        "privilege": el.privilege.model_dump() if el.privilege else None,
        "privilege_label": _privilege(el, lang),
        "refines": el.refines,
        "refines_title": target.title if target else "",
        "refined_by": [
            f"{s.name}/{e.id}" for s, e in topology.refined_by(project, sub.name, el.id)
        ],
        "listens_on": [x.model_dump() for x in el.listens_on],
        "listens_on_label": "; ".join(_listener(x) for x in el.listens_on),
        "authentication": el.authentication,
        "authentication_label": t(f"authentication.{el.authentication}", lang)
        if el.authentication
        else None,
        "memory_safe": el.memory_safe,
        "sbom_ref": " / ".join(v for v in (ref.purl, ref.cpe) if v) if ref else None,
    }


def _evaluation(method: Method, threat: Threat, project: Project, residual: bool) -> Ctx | None:
    if residual and threat.residual is None:
        return None
    ev = evaluate(method, threat, project.config, residual=residual)
    return {
        "exposure": ev.exposure,
        "impact": ev.impact,
        "risk": ev.risk,
        "max_acceptable_risk": ev.max_acceptable_risk,
        "acceptable": ev.acceptable,
        "rules": ev.rules,
    }


def _env_labels(method: Method, env: Any, lang: Lang) -> Ctx:
    out: Ctx = {}
    for name in ("interface", "access", "user"):
        value = getattr(env, name)
        entry = method.indicator(name).values.get(value) if value else None
        out[name] = value
        out[f"{name}_label"] = getattr(entry, lang) if entry else (value or "–")
    return out


def _model_data(
    project: Project,
    sub: SubModel,
    method: Method,
    lang: Lang,
    cra: dict[str, str],
    prefix: str = "",
) -> Ctx:
    """`prefix` (`<model>/`) qualifies the ids of a sub-model shown in its parent's document."""
    titles = _titles(sub)
    objs = sub.objects
    zones = {z.id: z.title for z in sub.meta.zones}
    assets_typed: dict[str, Asset] = {
        i: o for i, o in objs["assets"].items() if isinstance(o, Asset)
    }

    assets = []
    for asset in assets_typed.values():
        cia = asset_impact(method, assets_typed, asset.id)
        assets.append(
            {
                **_base(asset, sub, prefix),
                "asset_class": asset.asset_class,
                "c": cia["C"],
                "i": cia["I"],
                "a": cia["A"],
                "protects": [prefix + i for i in asset.protects],
                "configurations": asset.configurations,
            }
        )

    elements = []
    for el in objs["elements"].values():
        d = el.model_dump()
        if not isinstance(el, Element):
            continue
        d["zone"] = effective_zone(sub, el)
        elements.append(
            {
                **_base(el, sub, prefix),
                **_topology(project, sub, el, lang, prefix),
                "kind": d["kind"],
                "kind_label": t(f"kind.{d['kind']}", lang),
                "zone": d["zone"],
                "zone_title": zones.get(d["zone"] or "", d["zone"]),
                "configurations": d["configurations"],
                "sbom": d["sbom"],
            }
        )

    flows = []
    for fl in objs["flows"].values():
        d = fl.model_dump()
        flows.append(
            {
                **_base(fl, sub, prefix),
                "source": prefix + d["source"],
                "source_title": titles.get(d["source"], ""),
                "target": prefix + d["target"],
                "target_title": titles.get(d["target"], ""),
                "protocol": d["protocol"],
                "bidirectional": d["bidirectional"],
                "assets": [prefix + a for a in d["assets"]],
                "configurations": d["configurations"],
                "boundary": (b := topology.boundary(sub, fl)) if isinstance(fl, Flow) else None,
                "boundary_label": t(f"boundary.{b}", lang) if isinstance(fl, Flow) and b else None,
            }
        )

    measure_status = {i: getattr(m, "status", None) for i, m in objs["measures"].items()}
    threats: list[Ctx] = []
    rejected: list[Ctx] = []
    for th in objs["threats"].values():
        if not isinstance(th, Threat):
            continue
        ev = _evaluation(method, th, project, residual=False) or {}
        res = _evaluation(method, th, project, residual=True)
        acceptable = ev.get("acceptable")
        treatment = (
            "unassessed" if acceptable is None else ("acceptable" if acceptable else "to_treat")
        )
        item = {
            **_base(th, sub, prefix),
            "stride": list(th.stride),
            "stride_names": [t(f"stride.{s}", lang) for s in th.stride],
            "targets": _refs(th.targets, titles, prefix),
            "assets": _refs(th.assets, titles, prefix),
            "configurations": th.configurations,
            "cyber_cause": th.cyber_cause,
            "scenario": th.scenario,
            "consequence": th.consequence,
            "safety_related": th.safety_related,
            "finding": th.finding,
            "assessment": {
                **_env_labels(method, th.assessment, lang),
                "impact": th.assessment.impact,
                "rationale": th.assessment.rationale,
            },
            **ev,
            "treatment": treatment,
            "treatment_label": t(treatment, lang),
            "residual": None
            if res is None or th.residual is None
            else {
                **res,
                **_env_labels(method, th.residual, lang),
                "rationale": th.residual.rationale,
            },
            "measures": [
                {
                    "id": prefix + i,
                    "title": titles.get(i, ""),
                    "status": measure_status.get(i),
                    "status_label": t(f"measure_status.{measure_status.get(i)}", lang)
                    if measure_status.get(i)
                    else "–",
                }
                for i in th.measures
            ],
            "questions": _refs(th.questions, titles, prefix),
            "cra_refs": [{"id": c, "title": cra.get(c, "")} for c in th.cra_refs],
            "vulnerabilities": list(th.vulnerabilities),
            "status": th.status,
            "status_label": t(f"threat_status.{th.status}", lang),
            "acceptance": th.acceptance.model_dump() if th.acceptance else None,
            "rejection": th.rejection.model_dump() if th.rejection else None,
        }
        (rejected if th.status == "rejected" else threats).append(item)

    measures = []
    for ms in objs["measures"].values():
        d = ms.model_dump(mode="json")
        measures.append(
            {
                **_base(ms, sub, prefix),
                "kind": d["kind"],
                "kind_label": t(f"measure_kind.{d['kind']}", lang) if d["kind"] else "–",
                "compensating": d["compensating"],
                "owner": d["owner"],
                "status": d["status"],
                "status_label": t(f"measure_status.{d['status']}", lang),
                "due": ms.model_dump()["due"],
                "evidence": d["evidence"],
                "evidence_refs": d["evidence_refs"],
                "cra_refs": [{"id": c, "title": cra.get(c, "")} for c in d["cra_refs"]],
                "threats": [
                    {"id": th["id"], "title": th["title"]}
                    for th in threats
                    if any(m["id"] == prefix + ms.id for m in th["measures"])
                ],
            }
        )

    questions = []
    for q in objs["questions"].values():
        d = q.model_dump()
        questions.append(
            {
                **_base(q, sub, prefix),
                "addressee": d["addressee"],
                "status": d["status"],
                "status_label": t(f"question_status.{d['status']}", lang),
                "answer": d["answer"],
                "threats": _refs(d["threats"], titles, prefix),
            }
        )

    return {
        "assets": assets,
        "elements": elements,
        "flows": flows,
        "threats": sort_by_risk(threats),
        "rejected_threats": rejected,
        "measures": measures,
        "questions": questions,
    }


def _model_meta(sub: SubModel, method: Method, lang: Lang) -> Ctx:
    meta = sub.meta
    return {
        "name": sub.name,
        "title": meta.title,
        "uuid": str(meta.uuid),
        "description": meta.description,
        "configurations": [c.model_dump() for c in meta.configurations],
        "zones": [
            {**z.model_dump(exclude={"environment"}), **_env_labels(method, z.environment, lang)}
            for z in meta.zones
        ],
        "changelog": [{**c.model_dump(), "model": sub.name} for c in meta.changelog],
    }


def _method_data(method: Method, lang: Lang) -> Ctx:
    acc = method.acceptance
    risk_labels = {k: _i18n(v, lang) for k, v in method.risk_levels.levels.items()}
    reading = method.risk_matrix.matrix_row_from_exposure
    return {
        "id": method.id,
        "title": _i18n(method.title, lang),
        "matrix_reading": reading,
        "matrix_note": t(f"matrix_note.{reading}", lang),
        "max_acceptable_risk": acc.max_acceptable_risk,
        "max_acceptable_label": risk_labels.get(acc.max_acceptable_risk, "–"),
        "acceptance_text": t("acceptance_text", lang).format(
            label=risk_labels.get(acc.max_acceptable_risk, "–"), level=acc.max_acceptable_risk
        ),
        "exposure_text": t("exposure_text", lang).format(
            offset=method.exposure.offset, scale=method.exposure.scale
        ),
        "risk_levels": [{"level": k, "label": v} for k, v in sorted(risk_labels.items())],
        "impact_levels": [
            {"level": k, "label": _i18n(v, lang)}
            for k, v in sorted(method.impact_levels.levels.items())
        ],
        "rules": [
            {
                "id": r.id,
                "label": _i18n(r.label, lang),
                "enabled": r.enabled,
                "source": r.source,
                "max_acceptable_risk": r.max_acceptable_risk,
                "impact_delta": r.impact_delta,
            }
            for r in acc.rules
        ],
        "approvers": {int(k): list(v) for k, v in sorted(acc.approvers.items())},
        # Effective matrix (reading applied): highest exposure first.
        "matrix": [
            {
                "exposure": e,
                "risks": [risk(method, e, i) for i in sorted(method.impact_levels.levels)],
            }
            for e in sorted(method.risk_matrix.rows, reverse=True)
        ],
    }


def _acceptance(project: Project, method: Method, lang: Lang, risk_labels: dict[int, str]) -> Ctx:
    """Decision points with options and, per option, how many threats need treatment."""
    default = _builtin_method(method)
    threats = [
        th
        for sub in project.models.values()
        for th in sub.objects["threats"].values()
        if isinstance(th, Threat) and th.status != "rejected"
    ]

    def to_treat(m: Method) -> int:
        return sum(evaluate(m, th, project.config).acceptable is False for th in threats)

    def with_acceptance(**update: Any) -> Method:
        return method.model_copy(update={"acceptance": method.acceptance.model_copy(update=update)})

    def option(label: str, current: bool, recommended: bool, count: int | None) -> Ctx:
        return {"label": label, "current": current, "recommended": recommended, "to_treat": count}

    decisions: list[Ctx] = []
    acc = method.acceptance
    decisions.append(
        {
            "id": "max_acceptable_risk",
            "title": t("decision.max_acceptable_risk", lang),
            "question": t("decision.max_acceptable_risk.q", lang),
            "options": [
                option(
                    f"{lvl} – {label}",
                    lvl == acc.max_acceptable_risk,
                    lvl == default.acceptance.max_acceptable_risk,
                    to_treat(with_acceptance(max_acceptable_risk=lvl)),
                )
                for lvl, label in sorted(risk_labels.items())
            ],
        }
    )
    decisions.append(
        {
            "id": "matrix_reading",
            "title": t("decision.matrix_reading", lang),
            "question": t("decision.matrix_reading.q", lang),
            "note": t(f"matrix_note.{default.risk_matrix.matrix_row_from_exposure}", lang),
            "options": [
                option(
                    t(f"option.{reading}", lang),
                    reading == method.risk_matrix.matrix_row_from_exposure,
                    reading == default.risk_matrix.matrix_row_from_exposure,
                    to_treat(
                        method.model_copy(
                            update={
                                "risk_matrix": method.risk_matrix.model_copy(
                                    update={"matrix_row_from_exposure": reading}
                                )
                            }
                        )
                    ),
                )
                for reading in ("inverted", "literal")
            ],
        }
    )
    default_rules = {r.id: r.enabled for r in default.acceptance.rules}
    for rule in acc.rules:
        decisions.append(
            {
                "id": f"rule:{rule.id}",
                "title": _i18n(rule.label, lang),
                "question": t("decision.rule.q", lang),
                "note": f"{t('col.source', lang)}: {rule.source}" if rule.source else None,
                "options": [
                    option(
                        t(f"option.{'enabled' if on else 'disabled'}", lang),
                        rule.enabled == on,
                        default_rules.get(rule.id, False) == on,
                        to_treat(
                            with_acceptance(
                                rules=[
                                    r.model_copy(update={"enabled": on}) if r.id == rule.id else r
                                    for r in acc.rules
                                ]
                            )
                        ),
                    )
                    for on in (False, True)
                ],
            }
        )
    named = bool(acc.approvers)
    decisions.append(
        {
            "id": "approvers",
            "title": t("decision.approvers", lang),
            "question": t("decision.approvers.q", lang),
            "note": "; ".join(
                f"{risk_labels.get(int(k), k)}: {', '.join(v)}"
                for k, v in sorted(acc.approvers.items())
            )
            or None,
            "options": [
                option(
                    t("option.approvers_any", lang),
                    not named,
                    not default.acceptance.approvers,
                    None,
                ),
                option(
                    t("option.approvers_named", lang),
                    named,
                    bool(default.acceptance.approvers),
                    None,
                ),
            ],
        }
    )
    for d in decisions:
        d["current"] = next((o["label"] for o in d["options"] if o["current"]), "–")
        d["recommended"] = next((o["label"] for o in d["options"] if o["recommended"]), "–")
    return {
        "threats_total": len(threats),
        "assessed_total": sum(
            evaluate(method, th, project.config).risk is not None for th in threats
        ),
        "current_to_treat": to_treat(method),
        "decisions": decisions,
        "approvers": sorted({n for names in acc.approvers.values() for n in names}),
    }


def _risk_distribution(threats: list[Ctx], method: Ctx) -> list[Ctx]:
    rows = []
    for lvl in reversed(method["risk_levels"]):
        count = sum(th["risk"] == lvl["level"] for th in threats)
        ok = lvl["level"] <= method["max_acceptable_risk"]
        rows.append({**lvl, "count": count, "acceptable": ok})
    return rows


def _approvals(threats: list[Ctx], rejected: list[Ctx], lang: Lang) -> list[Ctx]:
    """Accepted and rejected threats with who decided, in which role and when."""
    rows = []
    for th in [*threats, *rejected]:
        decision = th["acceptance"] if th["status"] == "accepted" else th["rejection"]
        if th["status"] not in ("accepted", "rejected") or decision is None:
            continue
        rows.append(
            {
                "threat": th["id"],
                "threat_title": th["title"],
                "model": th["model"],
                "decision": th["status"],
                "decision_label": t(f"threat_status.{th['status']}", lang),
                "risk": th["risk"],
                "by": decision["by"],
                "role": decision["role"],
                "date": decision["date"],
                "rationale": decision["rationale"],
            }
        )
    return sorted(rows, key=lambda r: (r["date"] is None, r["date"] or "", r["threat"]))


def _custom_fields(project: Project, items: dict[str, list[Ctx]], lang: Lang) -> list[Ctx]:
    labels: dict[tuple[str, str], str] = {}
    for obj_type, defs in project.custom_fields.fields.items():
        for f in defs:
            labels[(obj_type, f.name)] = f.label.get(lang) or f.name
    rows = []
    for collection, objs in items.items():
        obj_type = collection.removesuffix("s")
        for obj in objs:
            for name, value in sorted(obj["custom"].items()):
                rows.append(
                    {
                        "object": obj["id"],
                        "object_type": obj_type,
                        "field": name,
                        "label": labels.get((obj_type, name), name),
                        "value": value,
                    }
                )
    return rows


def filters_for(method: Method, lang: Lang) -> Filters:
    risk_labels = {k: _i18n(v, lang) for k, v in method.risk_levels.levels.items()}
    impact_labels = {k: _i18n(v, lang) for k, v in method.impact_levels.levels.items()}
    return make_filters(lang, risk_labels, impact_labels)


def build_context(
    project: Project, method: Method, meta: TemplateMeta, model_name: str | None
) -> Ctx:
    """The complete template context; keys are listed in KNOWN_VARIABLES."""
    lang: Lang = meta.language or project.config.language
    risk_labels = {k: _i18n(v, lang) for k, v in method.risk_levels.levels.items()}
    filters = filters_for(method, lang)
    if model_name:  # one document per product: the model plus the sub-models refining it
        subs = [project.models[model_name], *topology.submodels(project, model_name)]
    else:
        subs = list(project.models.values())
    names = {s.name for s in subs}
    # ids of a sub-model shown with its parent are qualified (`software/T-0001`)
    prefixes = {
        s.name: f"{s.name}/" if topology.parent_model(project, s) in names else "" for s in subs
    }
    cra_cat = load_catalog("cra").entries
    inv = sbom.inventory(project)
    cra = {k: (v.get(lang, "") if isinstance(v, dict) else v) for k, v in cra_cat.items()}

    data: dict[str, list[Ctx]] = {}
    for sub in subs:
        for key, value in _model_data(project, sub, method, lang, cra, prefixes[sub.name]).items():
            data.setdefault(key, []).extend(value)
    for key in ("assets", "elements", "flows", "rejected_threats", "measures", "questions"):
        data.setdefault(key, [])
    data["threats"] = sort_by_risk(data.get("threats", []))

    models = [_model_meta(s, method, lang) for s in subs]
    changelog = sorted(
        (c for m in models for c in m["changelog"]), key=lambda c: (c["date"], c["version"])
    )
    latest = changelog[-1] if changelog else None
    method_data = _method_data(method, lang)
    ctx: Ctx = {
        "lang": lang,
        "project": {
            **project.config.model_dump(
                include={"name", "uuid", "method", "language", "lifecycle"}, mode="json"
            ),
            "support_until": project.config.support_until,
            "next_review": project.config.next_review,
            "lifecycle_label": t(f"lifecycle.{project.config.lifecycle}", lang),
        },
        "model": models[0] if meta.scope == "model" and models else None,
        "models": models,
        "document": {
            "title": _i18n(meta.name, lang),
            "template": meta.id,
            "scope": meta.scope,
            "version": latest["version"] if latest else None,
            "date": latest["date"] if latest else None,
            "generator": PRODUCT_NAME,
        },
        "method": method_data,
        **data,
        "changelog": list(reversed(changelog)),
        "traceability": [
            {
                "threat": th["id"],
                "threat_title": th["title"],
                "risk": th["risk"],
                "measure": m["id"] if m else None,
                "measure_title": m["title"] if m else None,
                "measure_status": m["status_label"] if m else None,
                "cra_refs": next(
                    (x["cra_refs"] for x in data["measures"] if m and x["id"] == m["id"]), []
                ),
            }
            for th in data["threats"]
            for m in (th["measures"] or [None])
        ],
        "risk_distribution": _risk_distribution(data["threats"], method_data),
        "unassessed_count": sum(th["risk"] is None for th in data["threats"]),
        "custom_fields": _custom_fields(
            project,
            {
                k: data[k]
                for k in ("elements", "flows", "assets", "threats", "measures", "questions")
            },
            lang,
        ),
        "acceptance": _acceptance(project, method, lang, risk_labels),
        "approvals": _approvals(data["threats"], data["rejected_threats"], lang),
        "revision": asdict(rev) if (rev := revision(project.root)) else None,
        "cra_requirements": [
            {
                **asdict(r),
                "title": r.title[lang],
                "status_label": t(f"cra_status.{r.status}", lang),
                "model": sub.name,
            }
            for sub in subs
            if not prefixes[sub.name]  # covered with the model it refines
            for r in cra_coverage(sub, [s for s in subs if s is not sub and prefixes[s.name]])
        ],
        "vulnerabilities": [
            {
                **asdict(v),
                "element": prefixes[sub.name] + v.element,
                "open": v.open,
                "element_title": _titles(sub).get(v.element, ""),
                "state_label": t(f"vuln_state.{v.state}", lang),
                "model": sub.name,
            }
            for sub in subs
            for v in sbom.findings(sub, inv)
        ],
    }
    env = make_env(filters)
    ctx["outline"] = build_outline(meta.outline, ctx, env, filters)
    return ctx
