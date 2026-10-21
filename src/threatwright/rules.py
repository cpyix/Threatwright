"""Validation rules. GUI, CLI and CI all call `validate()` (principle 7).

Rule codes are stable identifiers; docs/validation-rules.md describes each.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from threatwright import sbom
from threatwright.cra import coverage as cra_coverage
from threatwright.library import check_library_refs, load_catalog, load_libraries
from threatwright.method import Method, MethodError, evaluate, load_method
from threatwright.model.objects import (
    Asset,
    CustomField,
    Element,
    Flow,
    Measure,
    ModelObject,
    Question,
    Threat,
)
from threatwright.model.store import DEFAULT_PREFIXES, MODEL_FILE, Issue, Project, SubModel

TEXT_FIELDS = ("title", "description", "scenario", "consequence", "evidence", "answer")
ASSESSED = {"assessed", "treated", "accepted"}
OPEN = {"identified", "assessed", "treated"}


@dataclass
class _Ctx:
    project: Project
    sub: SubModel
    method: Method | None
    uuids: dict[str, str]
    issues: list[Issue] = field(default_factory=list)

    def add(
        self,
        severity: Literal["error", "warning"],
        code: str,
        collection: str,
        obj: ModelObject,
        location: str,
        message: str,
    ) -> None:
        path = self.project.root / "models" / self.sub.name / collection / f"{obj.id}.yaml"
        self.issues.append(Issue(path, location, message, code, severity, self.sub.name, obj.id))

    def ids(self, collection: str) -> set[str]:
        return set(self.sub.objects[collection])


def validate(project: Project) -> list[Issue]:
    issues = list(project.issues)
    method: Method | None = None
    try:
        method = load_method(project.root, project.config)
    except MethodError as exc:
        issues.append(Issue(project.root, "method", str(exc), "method-invalid"))
    libs = load_libraries(project.config.libraries, project.root)
    issues += libs.issues
    issues += check_library_refs(project, libs)[0]
    cra = set(load_catalog("cra").entries)
    inv = sbom.inventory(project)
    issues += inv.issues
    uuids: dict[str, str] = {}
    for sub in project.models.values():
        ctx = _Ctx(project, sub, method, uuids)
        _check_model(ctx)
        _check_cra_requirements(ctx, cra)
        _check_vulnerabilities(ctx, inv)
        for coll, objects in sub.objects.items():
            for obj in objects.values():
                for ref in getattr(obj, "cra_refs", []):
                    if ref not in cra:
                        ctx.add(
                            "warning",
                            "unknown-cra-ref",
                            coll,
                            obj,
                            "cra_refs",
                            f"'{ref}' is not in the CRA catalog",
                        )
        issues += ctx.issues
    return issues


def _check_model(ctx: _Ctx) -> None:
    sub = ctx.sub
    elements, flows = ctx.ids("elements"), ctx.ids("flows")
    assets, measures, questions = ctx.ids("assets"), ctx.ids("measures"), ctx.ids("questions")
    all_ids = set().union(*(ctx.ids(c) for c in sub.objects))
    zones = {z.id for z in sub.meta.zones}
    configs = {c.id for c in sub.meta.configurations}
    prefixes = {**DEFAULT_PREFIXES, **sub.meta.id_prefixes}.values()
    id_in_text = re.compile(rf"\b(?:{'|'.join(map(re.escape, prefixes))})-\d{{4,}}\b")
    threats = _of(sub, "threats", Threat)

    def refs(coll: str, obj: ModelObject, loc: str, values: list[str], valid: set[str]) -> None:
        for v in values:
            if v not in valid:
                ctx.add("error", "unresolved-ref", coll, obj, loc, f"'{v}' does not exist")

    for coll, objects in sub.objects.items():
        for obj in objects.values():
            key = str(obj.uuid)
            if key in ctx.uuids:
                ctx.add(
                    "error", "duplicate-uuid", coll, obj, "uuid", f"also used by {ctx.uuids[key]}"
                )
            ctx.uuids[key] = f"{sub.name}/{obj.id}"
            unknown_cfg = [c for c in getattr(obj, "configurations", []) if c not in configs]
            for c in unknown_cfg:
                ctx.add("error", "unknown-configuration", coll, obj, "configurations", f"'{c}'")
            for loc, text in _texts(obj):
                for found in id_in_text.findall(text):
                    if found not in all_ids:
                        ctx.add("error", "unresolved-text-ref", coll, obj, loc, f"'{found}'")
            _check_custom(ctx, coll, obj, all_ids)

    for e in _of(sub, "elements", Element):
        if e.zone is not None and e.zone not in zones:
            ctx.add("error", "unknown-zone", "elements", e, "zone", f"'{e.zone}'")
    for f in _of(sub, "flows", Flow):
        refs("flows", f, "source", [f.source], elements)
        refs("flows", f, "target", [f.target], elements)
        refs("flows", f, "assets", f.assets, assets)
    for obj in _elements_and_flows(sub):
        coll = "elements" if isinstance(obj, Element) else "flows"
        for cat, why in obj.stride_not_relevant.items():
            if not why.strip():
                ctx.add(
                    "error",
                    "missing-rationale",
                    coll,
                    obj,
                    f"stride_not_relevant.{cat}",
                    "'not relevant' needs a rationale",
                )

    for a in _of(sub, "assets", Asset):
        refs("assets", a, "protects", a.protects, assets)
        if ctx.method is not None:
            cls = ctx.method.asset_classes.get(a.asset_class)
            if cls is None:
                ctx.add(
                    "error",
                    "unknown-asset-class",
                    "assets",
                    a,
                    "asset_class",
                    f"'{a.asset_class}' is not defined by the method",
                )
            elif any(isinstance(v, list) for v in (cls.c, cls.i, cls.a)) and not a.protects:
                ctx.add(
                    "error",
                    "security-asset-without-protects",
                    "assets",
                    a,
                    "protects",
                    "security assets inherit their impact from the assets they protect",
                )
        amp = a.amplifier
        if (
            amp
            and (amp.c, amp.i, amp.a) != (None, None, None)
            and not (amp.rationale or "").strip()
        ):
            ctx.add(
                "error",
                "missing-rationale",
                "assets",
                a,
                "amplifier.rationale",
                "an amplifier needs a rationale",
            )

    for t in threats:
        _check_threat(ctx, t, elements | flows, assets, measures, questions)

    referenced_measures = {m for t in threats for m in t.measures}
    for m in _of(sub, "measures", Measure):
        for ref in m.evidence_refs:
            is_link = ref.startswith(("http://", "https://"))
            if not is_link and not (ctx.project.root / ref).is_file():
                ctx.add("error", "evidence-missing", "measures", m, "evidence_refs", ref)
        if m.status == "implemented" and not (m.evidence or "").strip() and not m.evidence_refs:
            ctx.add(
                "warning",
                "implemented-without-evidence",
                "measures",
                m,
                "evidence",
                "an implemented measure needs evidence (text, file or link)",
            )
        if m.id not in referenced_measures:
            ctx.add(
                "warning",
                "measure-unreferenced",
                "measures",
                m,
                "",
                "no threat references this measure",
            )
    referenced_questions = {q for t in threats for q in t.questions}
    for q in _of(sub, "questions", Question):
        refs("questions", q, "threats", q.threats, ctx.ids("threats"))
        if not q.threats and q.id not in referenced_questions:
            ctx.add(
                "warning",
                "question-unreferenced",
                "questions",
                q,
                "threats",
                "question is not linked to a threat",
            )

    _check_coverage(ctx, threats)


def _check_threat(
    ctx: _Ctx, t: Threat, targets: set[str], assets: set[str], measures: set[str], qs: set[str]
) -> None:
    def err(code: str, loc: str, msg: str) -> None:
        ctx.add("error", code, "threats", t, loc, msg)

    def warn(code: str, loc: str, msg: str) -> None:
        ctx.add("warning", code, "threats", t, loc, msg)

    for loc, values, valid in (
        ("targets", t.targets, targets),
        ("assets", t.assets, assets),
        ("measures", t.measures, measures),
        ("questions", t.questions, qs),
    ):
        for v in values:
            if v not in valid:
                err("unresolved-ref", loc, f"'{v}' does not exist")
    if not t.targets:
        warn("threat-without-target", "targets", "threat is not attached to an element or flow")

    method = ctx.method
    for prefix, a in (("assessment", t.assessment), ("residual", t.residual)):
        if a is None or method is None:
            continue
        for name in ("interface", "access", "user"):
            value = getattr(a, name)
            if value is not None and value not in method.indicator(name).values:
                err("unknown-indicator-value", f"{prefix}.{name}", f"'{value}' is not defined")

    a = t.assessment
    if t.status in ASSESSED and None in (a.interface, a.access, a.user, a.impact):
        err(
            "incomplete-assessment",
            "assessment",
            f"status '{t.status}' needs interface, access, user and impact",
        )
    if t.status in OPEN and not t.measures:
        err(
            "threat-without-measure",
            "measures",
            "open threat needs a measure, an acceptance or a rejection",
        )

    if t.status == "accepted":
        if t.acceptance is None or not t.acceptance.rationale.strip():
            err(
                "acceptance-without-rationale",
                "acceptance.rationale",
                "acceptance needs a rationale",
            )
        if method is not None:
            ev = evaluate(method, t, ctx.project.config)
            if ev.risk is not None and not ev.acceptable:
                err(
                    "acceptance-not-allowed",
                    "status",
                    f"risk {ev.risk} exceeds the acceptable limit {ev.max_acceptable_risk}",
                )
            allowed = method.acceptance.approvers.get(ev.risk) if ev.risk is not None else None
            acc = t.acceptance
            # approvers may be named as persons or as roles
            if allowed is not None and (acc is None or not {acc.by, acc.role} & set(allowed)):
                err(
                    "acceptance-not-authorized",
                    "acceptance.by",
                    f"risk {ev.risk} may only be accepted by: {', '.join(allowed)}",
                )
        missing = [
            f
            for f in ("by", "role", "date")
            if t.acceptance is None or getattr(t.acceptance, f) in (None, "")
        ]
        if missing:
            warn(
                "acceptance-undocumented",
                f"acceptance.{missing[0]}",
                f"the approval needs who, role and date (missing: {', '.join(missing)})",
            )
    if t.status == "rejected" and (t.rejection is None or not t.rejection.rationale.strip()):
        err("rejection-without-rationale", "rejection.rationale", "rejection needs a rationale")

    if t.cyber_cause is False and t.status != "rejected":
        warn(
            "not-a-cyber-risk",
            "cyber_cause",
            "cause is not an attack on the product: reject it with a rationale",
        )
    if t.cyber_cause is None and t.status in ASSESSED:
        warn("cyber-cause-unanswered", "cyber_cause", "is the cause an attack on the product?")
    if t.residual is not None and method is not None:
        ev = evaluate(method, t, ctx.project.config, residual=True)
        if ev.acceptable is False:
            warn(
                "residual-not-acceptable",
                "residual",
                f"residual risk {ev.risk} exceeds the limit {ev.max_acceptable_risk}",
            )


def _check_coverage(ctx: _Ctx, threats: list[Threat]) -> None:
    if ctx.method is None:
        return
    covered = {(target, s) for t in threats for target in t.targets for s in t.stride}
    targeted = {target for t in threats for target in t.targets}
    for obj in _elements_and_flows(ctx.sub):
        coll = "elements" if isinstance(obj, Element) else "flows"
        kind = obj.kind if isinstance(obj, Element) else "flow"
        if isinstance(obj, Element) and kind != "external" and obj.id not in targeted:
            ctx.add(
                "warning", "element-without-threat", coll, obj, "", "no threat targets this element"
            )
        for s in ctx.method.stride_per_kind.map.get(kind, []):
            if (obj.id, s) not in covered and s not in obj.stride_not_relevant:
                ctx.add(
                    "warning",
                    "coverage-gap",
                    coll,
                    obj,
                    f"stride.{s}",
                    f"no threat for STRIDE '{s}' and not marked as not relevant",
                )


def _check_cra_requirements(ctx: _Ctx, catalog: set[str]) -> None:
    path = ctx.project.root / "models" / ctx.sub.name / MODEL_FILE

    def add(severity: Literal["error", "warning"], code: str, loc: str, msg: str) -> None:
        ctx.issues.append(Issue(path, loc, msg, code, severity, ctx.sub.name))

    for req, why in ctx.sub.meta.cra_not_applicable.items():
        loc = f"cra_not_applicable.{req}"
        if req not in catalog:
            add("warning", "unknown-cra-ref", loc, f"'{req}' is not in the CRA catalog")
        if not why.strip():
            add("error", "missing-rationale", loc, "'not applicable' needs a rationale")
    if not ctx.sub.objects["threats"]:
        return  # analysis not started yet: no list of 21 gaps on an empty model
    for row in cra_coverage(ctx.sub):
        if row.status == "open":
            add(
                "warning",
                "cra-requirement-uncovered",
                f"cra_not_applicable.{row.id}",
                f"CRA requirement {row.id} has no threat or measure and is not marked "
                "as not applicable",
            )


def _check_vulnerabilities(ctx: _Ctx, inv: sbom.Inventory) -> None:
    invalid = {i.path.name for i in inv.issues if i.path is not None}
    for e in _of(ctx.sub, "elements", Element):
        for name in e.sbom:
            if name not in inv.sboms and name not in invalid:
                ctx.add("error", "sbom-missing", "elements", e, "sbom", f"{sbom.SBOM_DIR}/{name}")
    for f in sbom.findings(ctx.sub, inv):
        if f.open and not f.threats:
            element = ctx.sub.objects["elements"][f.element]
            ctx.add(
                "error",
                "vulnerability-untreated",
                "elements",
                element,
                "sbom",
                f"{f.vuln} ({f.state}) in {f.purl}: no threat lists it in `vulnerabilities`",
            )


def _of[T: ModelObject](sub: SubModel, collection: str, cls: type[T]) -> list[T]:
    return [o for o in sub.objects[collection].values() if isinstance(o, cls)]


def _elements_and_flows(sub: SubModel) -> list[Element | Flow]:
    return [*_of(sub, "elements", Element), *_of(sub, "flows", Flow)]


def _texts(obj: ModelObject) -> list[tuple[str, str]]:
    out = [(f, v) for f in TEXT_FIELDS if isinstance(v := getattr(obj, f, None), str)]
    if isinstance(obj, Threat):
        for prefix, a in (("assessment", obj.assessment), ("residual", obj.residual)):
            if a is not None and a.rationale:
                out.append((f"{prefix}.rationale", a.rationale))
    return out


def _check_custom(ctx: _Ctx, coll: str, obj: ModelObject, all_ids: set[str]) -> None:
    defs: list[CustomField] = ctx.project.custom_fields.fields.get(coll.removesuffix("s"), [])
    known = {d.name for d in defs}
    for key in obj.custom:
        if key not in known:
            ctx.add(
                "warning",
                "custom-unknown",
                coll,
                obj,
                f"custom.{key}",
                "field is not defined in custom-fields.yaml",
            )
    for d in defs:
        value: Any = obj.custom.get(d.name)
        loc = f"custom.{d.name}"
        if value in (None, "", []):
            if d.required:
                ctx.add("error", "custom-required", coll, obj, loc, "required field is empty")
            continue
        bad = (
            (d.type == "choice" and value not in d.options)
            or (d.type == "multichoice" and not set(_as_list(value)) <= set(d.options))
            or (d.type == "reference" and not set(_as_list(value)) <= all_ids)
            or (d.type == "bool" and not isinstance(value, bool))
            or (
                d.type == "number"
                and (isinstance(value, bool) or not isinstance(value, int | float))
            )
        )
        if bad:
            ctx.add("error", "custom-invalid", coll, obj, loc, f"invalid value for type {d.type}")


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def has_errors(issues: list[Issue], strict: bool = False) -> bool:
    return any(i.severity == "error" or strict for i in issues)


def relative(issue: Issue, root: Path) -> str:
    if issue.path is None:
        return ""
    try:
        return issue.path.relative_to(root).as_posix()
    except ValueError:
        return issue.path.as_posix()
