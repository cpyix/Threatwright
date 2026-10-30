"""Applicability of Adaptable Risk-based Controls (ARC), BSI TR-03183-1 §6 (p. 54-57).

A control carries one or more risk scenarios (§6.1, p. 54): prose, affected
assets with impact, and an environment (access restriction, interface
restriction, user capability). Per §6.2 (p. 54) a control applies to the PwDE
or a part of it if that part handles an asset with at least the listed impact
and expects one of the listed values for every environment parameter ("*"
matches any value).

The BSI's OSCAL encoding of risk scenarios is not public. Threatwright reads
them from control parts named `risk-scenario` (ADR-0012, assumption); imported
controls keep their parts in `oscal_extra.parts`, and hand-written library
entries use the same structure there.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from ruamel.yaml.comments import CommentedMap

from threatwright.library import Libraries, MeasureTemplate
from threatwright.method import Cia, Method, asset_impact, load_method
from threatwright.model.objects import Asset, Element, Environment, Strict, Threat
from threatwright.model.store import Project, merge_into, read_yaml, to_plain, write_yaml
from threatwright.topology import effective_zone, handled_assets

OVERRIDES_FILE = Path("profiles") / "arc-overrides.yaml"
SCENARIO_PART = "risk-scenario"
ENV_PROPS = {
    "interface": "interface-restriction",
    "access": "access-restriction",
    "user": "user-capability",
}
IMPACT = re.compile(r"^\s*([CIA])\s*[:(]\s*([1-5])\s*\)?\s*$")
EnvName = Literal["interface", "access", "user"]
ENV_LABELS = {
    "interface": ("Schnittstelle", "interface"),
    "access": ("Zugang", "access"),
    "user": ("Nutzer", "user"),
}


def normalize(value: str) -> str:
    """TR wording ("External network", "Layman") -> method key (external_network, layman)."""
    value = value.strip()
    return value if value == "*" else re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


@dataclass
class RiskScenario:
    prose: str = ""
    impact: dict[Cia, int] = field(default_factory=dict)  # minimum impact; empty = any
    asset_classes: list[str] = field(default_factory=list)  # empty = any
    environment: dict[str, list[str]] = field(default_factory=dict)  # missing / "*" = any


def risk_scenarios(entry: MeasureTemplate) -> list[RiskScenario]:
    found: list[RiskScenario] = []

    def walk(parts: list[Any]) -> None:
        for part in parts:
            if not isinstance(part, dict):
                continue
            if part.get("name") == SCENARIO_PART:
                found.append(_scenario(part))
            walk(part.get("parts", []))

    walk(entry.oscal_extra.get("parts", []))
    return found


def _scenario(part: dict[str, Any]) -> RiskScenario:
    s = RiskScenario(prose=str(part.get("prose", "")))
    for prop in part.get("props", []):
        name, value = prop.get("name"), str(prop.get("value", ""))
        if name == "asset-impact" and (m := IMPACT.match(value)):
            dim = cast(Cia, m[1])
            s.impact[dim] = min(s.impact.get(dim, 5), int(m[2]))
        elif name == "asset-class":
            s.asset_classes.append(value.strip())
        for env, prop_name in ENV_PROPS.items():
            if name == prop_name:
                s.environment.setdefault(env, []).append(normalize(value))
    return s


# --- model parts ----------------------------------------------------------------------


@dataclass
class _Asset:
    id: str
    title: str
    asset_class: str
    impact: dict[Cia, int | None]


@dataclass
class _Part:
    label: str
    env: dict[str, set[str]]
    assets: list[_Asset]


def _env(env: Environment) -> dict[str, set[str]]:
    return {name: {v} if (v := getattr(env, name)) else set() for name in ENV_PROPS}


def _parts(project: Project, model_name: str, method: Method, combined: bool) -> list[_Part]:
    """Elements (zone environment) and assessed threats, each with the assets they handle."""
    sub = project.models[model_name]
    assets = cast(dict[str, Asset], sub.objects["assets"])
    elements = cast(dict[str, Element], sub.objects["elements"])
    threats = cast(dict[str, Threat], sub.objects["threats"])
    zones = {z.id: z.environment for z in sub.meta.zones}

    def info(ids: list[str]) -> list[_Asset]:
        return [
            _Asset(a, assets[a].title, assets[a].asset_class, asset_impact(method, assets, a))
            for a in dict.fromkeys(ids)
            if a in assets
        ]

    parts: list[_Part] = []
    for el in elements.values():
        zone = effective_zone(sub, el)
        env = zones.get(zone) if zone else None
        handled = info(handled_assets(sub, el.id))
        parts.append(_Part(f"{el.id} {el.title}", _env(env or Environment()), handled))
    for t in threats.values():
        parts.append(_Part(f"{t.id} {t.title}", _env(t.assessment), info(t.assets)))
    if combined:  # §6.3 (p. 54-55): one profile of all assets and all environments
        merged: dict[str, set[str]] = {name: set() for name in ENV_PROPS}
        for p in parts:
            for name, values in p.env.items():
                merged[name] |= values
        return [_Part("combined", merged, info(list(assets)))]
    return parts


def _env_ok(s: RiskScenario, part: _Part) -> bool:
    return all(
        not wanted or "*" in wanted or bool(part.env[name] & set(wanted))
        for name, wanted in s.environment.items()
    )


def _asset_hit(s: RiskScenario, part: _Part) -> tuple[_Asset, Cia, int] | None | Literal[True]:
    """Matching asset with dimension and value; True when the scenario has no asset condition."""
    if not s.impact and not s.asset_classes:
        return True
    for a in part.assets:
        if s.asset_classes and a.asset_class not in s.asset_classes:
            continue
        if not s.impact:
            return a, "C", 0
        for dim, minimum in s.impact.items():
            value = a.impact.get(dim)
            if value is not None and value >= minimum:
                return a, dim, value
    return None


# --- result -------------------------------------------------------------------------


@dataclass
class ControlApplicability:
    measure_id: str
    control_id: str | None
    applies: bool
    rationale: dict[str, str]  # {"de": ..., "en": ...}
    part: str | None = None
    scenario: int | None = None  # 1-based index of the matching risk scenario
    overridden: bool = False


def _env_text(env: dict[str, set[str]] | dict[str, list[str]], lang: int) -> str:
    return ", ".join(f"{ENV_LABELS[n][lang]} {'/'.join(sorted(v)) or '?'}" for n, v in env.items())


def _requirement(s: RiskScenario, lang: int) -> str:
    alt = (" oder ", " or ")[lang]
    items = []
    if s.impact:
        items.append(alt.join(f"{d}≥{v}" for d, v in s.impact.items()))
    if s.asset_classes:
        items.append(("Assetklasse ", "asset class ")[lang] + "/".join(s.asset_classes))
    env = {n: v for n, v in s.environment.items() if v and "*" not in v}
    if env:
        items.append(_env_text(env, lang))
    return "; ".join(items) or ("keine Bedingung", "no condition")[lang]


def _applies(
    entry: MeasureTemplate, scenarios: list[RiskScenario], parts: list[_Part]
) -> ControlApplicability:
    control_id = entry.oscal_ref.control_id if entry.oscal_ref else None
    for n, s in enumerate(scenarios, 1):
        for part in parts:
            hit = _asset_hit(s, part) if _env_ok(s, part) else None
            if hit is None:
                continue
            if hit is True:
                why_de, why_en = "keine Asset-Bedingung", "no asset condition"
            else:
                a, dim, value = hit
                cond = f"{dim}={value}" if s.impact else a.asset_class
                why_de = f"Asset {a.id} ({a.title}) mit {cond}"
                why_en = f"asset {a.id} ({a.title}) with {cond}"
            rationale = {
                "de": f"Risikoszenario {n} trifft auf {part.label} zu: {why_de}; "
                f"Umgebung {_env_text(part.env, 0)} (TR-03183-1 §6.2, S. 54).",
                "en": f"Risk scenario {n} matches {part.label}: {why_en}; "
                f"environment {_env_text(part.env, 1)} (TR-03183-1 §6.2, p. 54).",
            }
            return ControlApplicability(entry.id, control_id, True, rationale, part.label, n)
    need_de = " | ".join(f"Szenario {n}: {_requirement(s, 0)}" for n, s in enumerate(scenarios, 1))
    need_en = " | ".join(f"scenario {n}: {_requirement(s, 1)}" for n, s in enumerate(scenarios, 1))
    rationale = {
        "de": "Kein Teil des Modells verarbeitet ein Asset mit der geforderten Auswirkung "
        f"in passender Umgebung ({need_de}; TR-03183-1 §6.2, S. 54).",
        "en": "No part of the model handles an asset with the required impact in a matching "
        f"environment ({need_en}; TR-03183-1 §6.2, p. 54).",
    }
    return ControlApplicability(entry.id, control_id, False, rationale)


def applicability(
    project: Project, model_name: str, library: Libraries, combined: bool = False
) -> list[ControlApplicability]:
    """Per library measure with risk scenarios: does it apply to the model? Overrides win."""
    method = load_method(project.root, project.config)
    parts = _parts(project, model_name, method, combined)
    overrides = load_overrides(project.root).models.get(model_name, {})
    out: list[ControlApplicability] = []
    for entry in sorted(library.measures.values(), key=lambda m: m.id):
        scenarios = risk_scenarios(entry)
        if not scenarios:
            continue
        result = _applies(entry, scenarios, parts)
        if (o := overrides.get(entry.id)) is not None:
            prefix = ("Manuell festgelegt", "Manual override")
            by = f" ({o.by})" if o.by else ""
            result.applies = o.applies
            result.overridden = True
            result.rationale = {
                "de": f"{prefix[0]}{by}: {o.rationale}",
                "en": f"{prefix[1]}{by}: {o.rationale}",
            }
        out.append(result)
    return out


# --- overrides -------------------------------------------------------------------------


class ArcOverride(Strict):
    applies: bool
    rationale: str
    by: str | None = None


class ArcOverrides(Strict):
    """Content of profiles/arc-overrides.yaml: model name -> library measure id -> decision."""

    schema_version: Literal[1] = 1
    models: dict[str, dict[str, ArcOverride]] = {}


def load_overrides(project_root: Path) -> ArcOverrides:
    path = Path(project_root) / OVERRIDES_FILE
    if not path.exists():
        return ArcOverrides()
    return ArcOverrides.model_validate(to_plain(read_yaml(path)))


def set_override(
    project_root: Path, model_name: str, measure_id: str, override: ArcOverride | None
) -> None:
    """Store or (with None) remove a manual decision; comments in the file survive."""
    path = Path(project_root) / OVERRIDES_FILE
    doc = read_yaml(path) if path.exists() else CommentedMap()
    data = load_overrides(project_root)
    per_model = data.models.setdefault(model_name, {})
    if override is None:
        per_model.pop(measure_id, None)
    else:
        per_model[measure_id] = override
    if not per_model:
        data.models.pop(model_name)
    if merge_into(doc, data) or not path.exists():
        write_yaml(path, doc)
