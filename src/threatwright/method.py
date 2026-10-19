"""Risk assessment method: configuration model and scoring.

All numbers come from the method YAML (default: methods/tr-03183-1). This
module only interprets them; it holds no methodology values itself.
"""

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from threatwright.model.objects import Assessment, Asset, ProjectConfig, Strict, Threat
from threatwright.model.store import read_yaml, to_plain

BUILTIN_METHODS = Path(__file__).parent / "methods"
METHOD_FILE = "method.yaml"
OVERRIDES_FILE = "method-overrides.yaml"
METHOD_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

Cia = Literal["C", "I", "A"]
CiaBase = int | list[Cia] | None


class Label(Strict):
    de: str
    en: str


class Scale(Strict):
    source: str
    levels: dict[int, Label]


class AssetClass(Strict):
    c: CiaBase = None
    i: CiaBase = None
    a: CiaBase = None
    source: str


class IndicatorValue(Strict):
    factor: Decimal = Field(ge=0, le=1)
    de: str
    en: str
    help: dict[Literal["de", "en"], str] = {}  # short own explanation shown at the field


class Indicator(Strict):
    source: str
    values: dict[str, IndicatorValue]


class Exposure(Strict):
    offset: Decimal
    scale: Decimal
    source: str
    note: str | None = None


class RiskMatrix(Strict):
    source: str
    rows: dict[int, list[int]]
    matrix_row_from_exposure: Literal["literal", "inverted"]


class AcceptanceRule(Strict):
    id: str
    label: Label
    source: str | None = None
    enabled: bool = False
    when: dict[str, Any] = {}
    max_acceptable_risk: int | None = None
    impact_delta: int = 0


class Acceptance(Strict):
    source: str
    max_acceptable_risk: int
    approvers: dict[int, list[str]] = {}
    rules: list[AcceptanceRule] = []


class Mapping(Strict):
    source: str
    map: dict[str, list[str]]


class Method(Strict):
    schema_version: Literal[1] = 1
    id: str
    title: Label
    source: dict[str, str] = {}
    impact_levels: Scale
    asset_classes: dict[str, AssetClass]
    interface: Indicator
    access: Indicator
    user: Indicator
    exposure: Exposure
    risk_levels: Scale
    risk_matrix: RiskMatrix
    acceptance: Acceptance
    stride_impact: Mapping
    stride_per_kind: Mapping

    @model_validator(mode="after")
    def _consistent(self) -> "Method":
        rows = self.risk_matrix.rows
        lo = int(self.exposure.offset)
        hi = int(self.exposure.offset + self.exposure.scale)
        if sorted(rows) != list(range(lo, hi + 1)):
            raise ValueError(f"risk_matrix.rows must cover environment {lo}..{hi}")
        n = len(self.impact_levels.levels)
        risks = set(self.risk_levels.levels)
        for key, row in rows.items():
            if len(row) != n or not set(row) <= risks:
                raise ValueError(f"risk_matrix row {key}: need {n} values from risk_levels")
        return self

    def indicator(self, name: str) -> Indicator:
        ind: Indicator = getattr(self, name)
        return ind


class MethodError(Exception):
    pass


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Mappings merge recursively; everything else (incl. lists) is replaced."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_method(project_root: Path, config: ProjectConfig) -> Method:
    """Project methods/<id> wins over the built-in one; then apply overrides."""
    if not METHOD_ID.match(config.method):
        raise MethodError(f"invalid method id '{config.method}'")
    candidates = [project_root / "methods" / config.method, BUILTIN_METHODS / config.method]
    path = next((p / METHOD_FILE for p in candidates if (p / METHOD_FILE).exists()), None)
    if path is None:
        raise MethodError(f"method '{config.method}' not found")
    try:
        data = to_plain(read_yaml(path))
        overrides = project_root / OVERRIDES_FILE
        if overrides.exists():
            data = deep_merge(data, to_plain(read_yaml(overrides)))
        return Method.model_validate(data)
    except Exception as exc:  # LoadError, ValidationError: report uniformly
        raise MethodError(f"{path}: {exc}") from exc


# --- scoring -------------------------------------------------------------------


def round_half_up(value: Decimal) -> int:
    """Commercial rounding (2.5 -> 3), unlike Python's round()."""
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def clamp(value: int, levels: Scale) -> int:
    return max(min(levels.levels), min(max(levels.levels), value))


def exposure(method: Method, env: Assessment) -> int | None:
    factors = []
    for name in ("interface", "access", "user"):
        value = getattr(env, name)
        entry = method.indicator(name).values.get(value) if value else None
        if entry is None:
            return None
        factors.append(entry.factor)
    product = factors[0] * factors[1] * factors[2]
    return round_half_up(method.exposure.offset + product * method.exposure.scale)


def risk(method: Method, exposure_value: int, impact: int) -> int:
    rows = method.risk_matrix.rows
    row = exposure_value
    if method.risk_matrix.matrix_row_from_exposure == "inverted":
        row = min(rows) + max(rows) - exposure_value
    return rows[row][impact - min(method.impact_levels.levels)]


def _lookup(ctx: dict[str, Any], dotted: str) -> Any:
    node: Any = ctx
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def matching_rules(method: Method, threat: Threat, config: ProjectConfig) -> list[AcceptanceRule]:
    ctx = {"threat": threat.model_dump(mode="json"), "project": config.model_dump(mode="json")}
    return [
        r
        for r in method.acceptance.rules
        if r.enabled and all(_lookup(ctx, k) == v for k, v in r.when.items())
    ]


@dataclass
class Evaluation:
    exposure: int | None = None
    impact: int | None = None
    risk: int | None = None
    max_acceptable_risk: int = 0
    acceptable: bool | None = None
    rules: list[str] = field(default_factory=list)


def evaluate(
    method: Method, threat: Threat, config: ProjectConfig, residual: bool = False
) -> Evaluation:
    """Exposure, effective impact, risk and acceptability; never stored."""
    rules = matching_rules(method, threat, config)
    limits = [r.max_acceptable_risk for r in rules if r.max_acceptable_risk is not None]
    result = Evaluation(
        max_acceptable_risk=min(limits, default=method.acceptance.max_acceptable_risk),
        rules=[r.id for r in rules],
    )
    assessment = threat.residual if residual else threat.assessment
    if assessment is None:
        return result
    result.exposure = exposure(method, assessment)
    if assessment.impact is not None:
        delta = sum(r.impact_delta for r in rules)
        result.impact = clamp(assessment.impact + delta, method.impact_levels)
    if result.exposure is not None and result.impact is not None:
        result.risk = risk(method, result.exposure, result.impact)
        result.acceptable = result.risk <= result.max_acceptable_risk
    return result


# --- asset impact ----------------------------------------------------------------


def asset_impact(
    method: Method, assets: dict[str, Asset], asset_id: str, _seen: frozenset[str] = frozenset()
) -> dict[Cia, int | None]:
    """Base impact per C/I/A incl. inheritance for security assets and amplifier."""
    asset = assets.get(asset_id)
    cls = method.asset_classes.get(asset.asset_class) if asset else None
    if asset is None or cls is None or asset_id in _seen:
        return {"C": None, "I": None, "A": None}
    out: dict[Cia, int | None] = {}
    for dim in ("C", "I", "A"):
        base: CiaBase = getattr(cls, dim.lower())
        value: int | None
        if isinstance(base, list):
            inherited = [
                v
                for p in asset.protects
                for d, v in asset_impact(method, assets, p, _seen | {asset_id}).items()
                if d in base and v is not None
            ]
            value = max(inherited, default=None)
        else:
            value = base
        amp = getattr(asset.amplifier, dim.lower()) if asset.amplifier else None
        if value is not None and amp is not None:
            value = clamp(round_half_up(Decimal(value) * Decimal(str(amp))), method.impact_levels)
        out[dim] = value
    return out


@dataclass
class ImpactSuggestion:
    impact: int
    asset_id: str
    dimension: Cia


def suggest_impact(
    method: Method, threat: Threat, assets: dict[str, Asset]
) -> ImpactSuggestion | None:
    """Highest impact among the threat's assets in the dimensions its STRIDE hits."""
    dims = {d for s in threat.stride for d in method.stride_impact.map.get(s, [])} or {
        "C",
        "I",
        "A",
    }
    best: ImpactSuggestion | None = None
    for asset_id in threat.assets:
        for dim, value in asset_impact(method, assets, asset_id).items():
            if dim in dims and value is not None and (best is None or value > best.impact):
                best = ImpactSuggestion(value, asset_id, dim)
    return best
