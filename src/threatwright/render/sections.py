"""Turn the outline of template.yaml into format-neutral content blocks.

Every bundled template (DOCX, ODT, Markdown, HTML) renders the same blocks, so
the formats never disagree. Block kinds: title, subtitle, h1, h2, p, note,
table (headers + rows), fields (label/value rows) and pagebreak.
"""

import re
from collections.abc import Callable
from typing import Any

from jinja2.sandbox import ImmutableSandboxedEnvironment

from threatwright.render.package import COLUMNS, Section

Ctx = dict[str, Any]
Block = dict[str, Any]
Filters = dict[str, Callable[..., Any]]
DASH = "–"


def _s(value: Any) -> str:
    if value is None or value == "" or value == []:
        return DASH
    if isinstance(value, bool):
        return "✓" if value else ""
    if isinstance(value, list):
        return ", ".join(_s(v) for v in value)
    if isinstance(value, dict) and "id" in value:
        return str(value["id"])
    return str(value)


def _refs(refs: list[Ctx], with_title: bool = False) -> str:
    if not refs:
        return DASH
    if with_title:
        return ", ".join(f"{r['id']} {r['title']}".strip() for r in refs)
    return ", ".join(r["id"] for r in refs)


def _level(value: Any, f: Filters, kind: str = "risk_label") -> str:
    return DASH if value is None else f"{value} – {f[kind](value)}"


def _getters(f: Filters) -> dict[str, dict[str, Callable[[Ctx], str]]]:
    tr = f["t"]
    return {
        "assets": {
            "id": lambda a: a["id"],
            "title": lambda a: a["title"],
            "asset_class": lambda a: a["asset_class"],
            "c": lambda a: _s(a["c"]),
            "i": lambda a: _s(a["i"]),
            "a": lambda a: _s(a["a"]),
            "protects": lambda a: _s(a["protects"]),
            "configurations": lambda a: _s(a["configurations"]),
            "description": lambda a: _s(a["description"]),
        },
        "elements": {
            "id": lambda e: e["id"],
            "title": lambda e: e["title"],
            "kind": lambda e: e["kind_label"],
            "zone": lambda e: _s(e["zone_title"]),
            "configurations": lambda e: _s(e["configurations"]),
            "description": lambda e: _s(e["description"]),
        },
        "flows": {
            "id": lambda x: x["id"],
            "title": lambda x: x["title"],
            "source": lambda x: f"{x['source']} {x['source_title']}".strip(),
            "target": lambda x: f"{x['target']} {x['target_title']}".strip(),
            "protocol": lambda x: _s(x["protocol"]),
            "assets": lambda x: _s(x["assets"]),
            "configurations": lambda x: _s(x["configurations"]),
            "description": lambda x: _s(x["description"]),
        },
        "threats": {
            "id": lambda th: th["id"],
            "title": lambda th: th["title"],
            "stride": lambda th: _s(th["stride"]),
            "targets": lambda th: _refs(th["targets"]),
            "exposure": lambda th: _s(th["exposure"]),
            "impact": lambda th: _level(th["impact"], f, "impact_label"),
            "risk": lambda th: _level(th["risk"], f),
            "treatment": lambda th: th["treatment_label"],
            "measures": lambda th: _refs(th["measures"]),
            "residual_risk": lambda th: (
                _level(th["residual"]["risk"], f) if th["residual"] else DASH
            ),
            "cra_refs": lambda th: _refs(th["cra_refs"]),
            "status": lambda th: th["status_label"],
        },
        "rejected": {
            "id": lambda th: th["id"],
            "title": lambda th: th["title"],
            "stride": lambda th: _s(th["stride"]),
            "targets": lambda th: _refs(th["targets"]),
            "rationale": lambda th: _s((th["rejection"] or {}).get("rationale")),
            "by": lambda th: _s((th["rejection"] or {}).get("by")),
        },
        "measures": {
            "id": lambda m: m["id"],
            "title": lambda m: m["title"],
            "kind": lambda m: m["kind_label"],
            "status": lambda m: m["status_label"],
            "owner": lambda m: _s(m["owner"]),
            "due": lambda m: f["date"](m["due"]) if m["due"] else DASH,
            "evidence": lambda m: _s(m["evidence"]),
            "threats": lambda m: _refs(m["threats"]),
            "cra_refs": lambda m: _refs(m["cra_refs"]),
        },
        "traceability": {
            "threat": lambda r: f"{r['threat']} {r['threat_title']}",
            "risk": lambda r: _level(r["risk"], f),
            "measure": lambda r: f"{r['measure']} {r['measure_title']}" if r["measure"] else DASH,
            "measure_status": lambda r: _s(r["measure_status"]),
            "cra": lambda r: _refs(r["cra_refs"], with_title=True),
        },
        "questions": {
            "id": lambda q: q["id"],
            "title": lambda q: q["title"],
            "addressee": lambda q: _s(q["addressee"]),
            "status": lambda q: q["status_label"],
            "answer": lambda q: _s(q["answer"]),
            "threats": lambda q: _refs(q["threats"]),
        },
        "risk_distribution": {
            "level": lambda r: str(r["level"]),
            "label": lambda r: r["label"],
            "count": lambda r: str(r["count"]),
            "treatment": lambda r: tr("acceptable" if r["acceptable"] else "to_treat"),
        },
        "changelog": {
            "model": lambda c: c["model"],
            "version": lambda c: c["version"],
            "date": lambda c: f["date"](c["date"]),
            "summary": lambda c: c["summary"],
            "author": lambda c: _s(c["author"]),
        },
        "approvals": {
            "threat": lambda r: f"{r['threat']} {r['threat_title']}",
            "status": lambda r: r["decision_label"],
            "risk": lambda r: _level(r["risk"], f),
            "by": lambda r: _s(r["by"]),
            "role": lambda r: _s(r["role"]),
            "date": lambda r: f["date"](r["date"]) if r["date"] else DASH,
            "rationale": lambda r: _s(r["rationale"]),
            "model": lambda r: r["model"],
        },
        "custom_fields": {
            "object": lambda c: c["object"],
            "field": lambda c: c["label"],
            "value": lambda c: _s(c["value"]),
        },
    }


class _Builder:
    def __init__(self, ctx: Ctx, env: ImmutableSandboxedEnvironment, f: Filters) -> None:
        self.ctx = ctx
        self.env = env
        self.f = f
        self.t: Callable[[str], str] = f["t"]
        self.getters = _getters(f)

    def table(self, kind: str, items: list[Ctx], columns: list[str] | None) -> list[Block]:
        if not items:
            return [{"kind": "p", "text": self.t("none")}]
        cols = columns or COLUMNS[kind][0]
        get = self.getters[kind]
        return [
            {
                "kind": "table",
                "columns": cols,
                "headers": [self.t(f"col.{c}") for c in cols],
                "rows": [[get[c](item) for c in cols] for item in items],
            }
        ]

    def fields(self, pairs: list[tuple[str, Any]]) -> Block:
        return {"kind": "fields", "rows": [[self.t(k), _s(v)] for k, v in pairs]}

    @staticmethod
    def raw_table(headers: list[str], rows: list[list[str]]) -> Block:
        return {"kind": "table", "columns": [], "headers": headers, "rows": rows}

    # --- section types -------------------------------------------------------

    def cover(self, s: Section) -> list[Block]:
        c = self.ctx
        model = c["model"]
        subtitle = c["project"]["name"] + (f" – {model['title']}" if model else "")
        pairs: list[tuple[str, Any]] = [("project", c["project"]["name"])]
        if model:
            pairs.append(("model", model["title"]))
        else:
            pairs.append(("models", [m["title"] for m in c["models"]]))
        pairs += [
            ("version", c["document"]["version"]),
            ("date", self.f["date"](c["document"]["date"], "long")),
            ("method", c["method"]["title"]),
            ("lifecycle", c["project"]["lifecycle_label"]),
        ]
        return [
            {"kind": "title", "text": c["document"]["title"]},
            {"kind": "subtitle", "text": subtitle},
            self.fields(pairs),
            {"kind": "pagebreak"},
        ]

    def scope(self, s: Section) -> list[Block]:
        out: list[Block] = []
        for m in self.ctx["models"]:
            if len(self.ctx["models"]) > 1:
                out.append({"kind": "h2", "text": f"{self.t('model')}: {m['title']}"})
            if m["description"]:
                out.append({"kind": "p", "text": m["description"]})
            out.append({"kind": "h2", "text": self.t("configurations")})
            out.append(
                self.raw_table(
                    [self.t("col.id"), self.t("col.title"), self.t("col.description")],
                    [[x["id"], x["title"], _s(x["description"])] for x in m["configurations"]],
                )
                if m["configurations"]
                else {"kind": "p", "text": self.t("none")}
            )
            out.append({"kind": "h2", "text": self.t("zones")})
            out.append(
                self.raw_table(
                    [self.t(f"col.{k}") for k in ("id", "title", "interface", "access", "user")],
                    [
                        [
                            z["id"],
                            z["title"],
                            z["interface_label"],
                            z["access_label"],
                            z["user_label"],
                        ]
                        for z in m["zones"]
                    ],
                )
                if m["zones"]
                else {"kind": "p", "text": self.t("none")}
            )
        return out

    def method(self, s: Section) -> list[Block]:
        m = self.ctx["method"]
        out: list[Block] = [
            {"kind": "p", "text": m["title"]},
            {"kind": "p", "text": m["exposure_text"]},
            {"kind": "note", "text": m["matrix_note"]},
            {"kind": "note", "text": m["acceptance_text"]},
            {"kind": "h2", "text": self.t("risk_matrix")},
            self.raw_table(
                [self.t("col.exposure")]
                + [f"{x['level']} {x['label']}" for x in m["impact_levels"]],
                [
                    [str(row["exposure"])] + [self.f["risk_label"](r) for r in row["risks"]]
                    for row in m["matrix"]
                ],
            ),
        ]
        if m["rules"]:
            out.append({"kind": "h2", "text": self.t("special_rules")})
            out.append(
                self.raw_table(
                    [self.t("col.title"), self.t("col.status"), self.t("col.source")],
                    [
                        [
                            r["label"],
                            self.t("enabled" if r["enabled"] else "disabled"),
                            _s(r["source"]),
                        ]
                        for r in m["rules"]
                    ],
                )
            )
        approvers = "; ".join(
            f"{self.f['risk_label'](k)}: {', '.join(v)}" for k, v in m["approvers"].items()
        )
        out.append({"kind": "p", "text": f"{self.t('approvers')}: {approvers or self.t('anyone')}"})
        out.append({"kind": "p", "text": self.t("computed_note")})
        return out

    def assets(self, s: Section) -> list[Block]:
        return self.table("assets", self.ctx["assets"], s.columns)

    def elements_and_flows(self, s: Section) -> list[Block]:
        return [
            {"kind": "h2", "text": self.t("elements")},
            *self.table("elements", self.ctx["elements"], s.columns),
            {"kind": "h2", "text": self.t("flows")},
            *self.table("flows", self.ctx["flows"], s.flow_columns),
        ]

    def threats(self, s: Section) -> list[Block]:
        out = self.table("threats", self.ctx["threats"], s.columns)
        if not s.details:
            return out
        for th in self.ctx["threats"]:
            a = th["assessment"]
            res = th["residual"]
            limit = _level(th["max_acceptable_risk"], self.f)
            if th["rules"]:
                limit += f" ({', '.join(th['rules'])})"
            pairs: list[tuple[str, Any]] = [
                ("col.stride", th["stride_names"]),
                ("col.targets", _refs(th["targets"], with_title=True)),
                ("col.assets", _refs(th["assets"], with_title=True)),
                ("col.configurations", th["configurations"]),
                ("scenario", th["scenario"]),
                ("consequence", th["consequence"]),
                ("safety_related", self.f["yesno"](th["safety_related"])),
                ("col.interface", a["interface_label"]),
                ("col.access", a["access_label"]),
                ("col.user", a["user_label"]),
                ("col.exposure", th["exposure"]),
                ("col.impact", _level(th["impact"], self.f, "impact_label")),
                ("col.risk", _level(th["risk"], self.f)),
                ("max_acceptable_risk", limit),
                ("col.treatment", th["treatment_label"]),
                ("col.rationale", a["rationale"]),
                (
                    "col.measures",
                    ", ".join(
                        f"{m['id']} {m['title']} ({m['status_label']})" for m in th["measures"]
                    )
                    or None,
                ),
                (
                    "col.residual_risk",
                    f"{_level(res['risk'], self.f)}"
                    + (
                        f" ({self.t('acceptable' if res['acceptable'] else 'to_treat')})"
                        if res["acceptable"] is not None
                        else ""
                    )
                    if res
                    else None,
                ),
                (
                    "col.cra_refs",
                    _refs(th["cra_refs"], with_title=True) if th["cra_refs"] else None,
                ),
                ("col.status", th["status_label"]),
            ]
            if th["acceptance"]:
                acc = th["acceptance"]
                who = (acc["by"] or DASH) + (f" ({acc['role']})" if acc["role"] else "")
                when = f", {self.f['date'](acc['date'])}" if acc["date"] else ""
                pairs.append(("acceptance", f"{who}{when}: {acc['rationale']}"))
            if th["questions"]:
                pairs.append(("questions", _refs(th["questions"], with_title=True)))
            out.append({"kind": "h2", "text": f"{th['id']} {th['title']}"})
            out.append(self.fields(pairs))
        return out

    def rejected(self, s: Section) -> list[Block]:
        return [
            {"kind": "p", "text": self.t("rejected_note")},
            *self.table("rejected", self.ctx["rejected_threats"], s.columns),
        ]

    def measures(self, s: Section) -> list[Block]:
        return self.table("measures", self.ctx["measures"], s.columns)

    def traceability(self, s: Section) -> list[Block]:
        return self.table("traceability", self.ctx["traceability"], s.columns)

    def questions(self, s: Section) -> list[Block]:
        return self.table("questions", self.ctx["questions"], s.columns)

    def risk_distribution(self, s: Section) -> list[Block]:
        assessed = sum(r["count"] for r in self.ctx["risk_distribution"])
        return [
            *self.table("risk_distribution", self.ctx["risk_distribution"], s.columns),
            self.fields(
                [("assessed_total", assessed), ("unassessed_count", self.ctx["unassessed_count"])]
            ),
            {"kind": "p", "text": self.t("rejected_note")},
        ]

    def changelog(self, s: Section) -> list[Block]:
        return self.table("changelog", self.ctx["changelog"], s.columns)

    def custom_fields(self, s: Section) -> list[Block]:
        return self.table("custom_fields", self.ctx["custom_fields"], s.columns)

    def approvals(self, s: Section) -> list[Block]:
        rev = self.ctx["revision"]
        if rev is None:
            basis = self.t("revision_none")
        else:
            basis = rev["commit"][:12] + (f" ({rev['tag']})" if rev["tag"] else "")
            if rev["dirty"]:
                basis += f", {self.t('revision_dirty')}"
        return [
            self.fields([("revision", basis)]),
            *self.table("approvals", self.ctx["approvals"], s.columns),
        ]

    def text(self, s: Section) -> list[Block]:
        source = s.text if isinstance(s.text, str) else getattr(s.text, self.ctx["lang"])
        rendered = self.env.from_string(source).render(self.ctx)
        return [
            {"kind": "p", "text": " ".join(p.split())}
            for p in re.split(r"\n\s*\n", rendered)
            if p.strip()
        ]

    def decisions(self, s: Section) -> list[Block]:
        out: list[Block] = []
        yes = "✓"
        for d in self.ctx["acceptance"]["decisions"]:
            out.append({"kind": "h2", "text": d["title"]})
            out.append({"kind": "p", "text": d["question"]})
            if d.get("note"):
                out.append({"kind": "note", "text": d["note"]})
            out.append(
                self.raw_table(
                    [self.t(f"col.{k}") for k in ("option", "recommended", "current", "to_treat")],
                    [
                        [
                            o["label"],
                            yes if o["recommended"] else "",
                            yes if o["current"] else "",
                            _s(o["to_treat"]),
                        ]
                        for o in d["options"]
                    ],
                )
            )
            out.append(
                self.fields(
                    [
                        ("recommendation", f"{d['recommended']} ({self.t('tr_default')})"),
                        ("current_setting", d["current"]),
                        ("decision", "______________________________"),
                    ]
                )
            )
        return out

    def signatures(self, s: Section) -> list[Block]:
        roles = (
            s.roles
            or self.ctx["acceptance"]["approvers"]
            or [
                self.t("role.product"),
                self.t("role.security"),
            ]
        )
        return [
            self.raw_table(
                [self.t(f"col.{k}") for k in ("name", "role", "date", "signature")],
                [["", r, "", ""] for r in roles],
            )
        ]

    def acceptance_impact(self, s: Section) -> list[Block]:
        acc = self.ctx["acceptance"]
        rows = [
            [d["title"], o["label"] + (" *" if o["current"] else ""), _s(o["to_treat"])]
            for d in acc["decisions"]
            for o in d["options"]
            if o["to_treat"] is not None
        ]
        basis = self.t("acceptance_basis").format(
            count=acc["assessed_total"], models=len(self.ctx["models"])
        )
        return [
            {"kind": "p", "text": basis},
            self.raw_table(
                [self.t("col.decision"), self.t("col.option"), self.t("col.to_treat")], rows
            ),
            {"kind": "p", "text": f"* {self.t('current_setting')}"},
        ]


def build_outline(
    outline: list[Section], ctx: Ctx, env: ImmutableSandboxedEnvironment, f: Filters
) -> list[Ctx]:
    b = _Builder(ctx, env, f)
    out = []
    for s in outline:
        if not s.enabled:
            continue
        if isinstance(s.title, str):
            title = s.title
        elif s.title is not None:
            title = getattr(s.title, ctx["lang"])
        else:
            title = b.t(f"section.{s.type}")
        blocks: list[Block] = getattr(b, s.type)(s)
        if title and s.type != "cover":
            blocks.insert(0, {"kind": "h1", "text": title})
        out.append({"type": s.type, "title": title, "blocks": blocks})
    return out
