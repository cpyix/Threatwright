import itertools
from decimal import Decimal
from pathlib import Path

import pytest

from threatwright.method import (
    MethodError,
    asset_impact,
    evaluate,
    exposure,
    load_method,
    risk,
    round_half_up,
    suggest_impact,
)
from threatwright.model.objects import Assessment, Asset, CiaAmplifier, ProjectConfig, Threat

# Independent copy of the matrix printed in TR-03183-1 v1.0.0, Annex D.2, p. 79.
PRINTED = {
    5: [1, 1, 1, 2, 3],
    4: [1, 1, 2, 3, 3],
    3: [2, 2, 3, 4, 4],
    2: [2, 3, 4, 4, 5],
    1: [2, 3, 4, 5, 5],
}
FACTORS = {  # Tables 11-13, p. 74-77
    "interface": {
        "physical": "0.38",
        "local": "0.55",
        "dedicated_known_network": "0.70",
        "known_network": "0.80",
        "external_network": "1.0",
    },
    "access": {
        "restricted": "0.42",
        "public_restricted": "0.58",
        "movable": "0.81",
        "non_restricted": "1.0",
    },
    "user": {"non_user_related": "1.0", "skilled": "0.58", "instructed": "0.81", "layman": "1.0"},
}


def method_for(tmp_path: Path, overrides: str = "") -> tuple:  # type: ignore[type-arg]
    tmp_path.mkdir(parents=True, exist_ok=True)
    if overrides:
        (tmp_path / "method-overrides.yaml").write_text(overrides, encoding="utf-8")
    config = ProjectConfig(name="t")
    return load_method(tmp_path, config), config


@pytest.fixture
def tr(tmp_path: Path):  # type: ignore[no-untyped-def]
    return method_for(tmp_path)[0]


@pytest.mark.parametrize("env,impact", list(itertools.product(range(1, 6), range(1, 6))))
def test_every_matrix_cell_in_both_readings(tmp_path: Path, env: int, impact: int) -> None:
    literal, _ = method_for(tmp_path / "l", "risk_matrix: {matrix_row_from_exposure: literal}")
    inverted, _ = method_for(tmp_path / "i")
    assert risk(literal, env, impact) == PRINTED[env][impact - 1]
    assert risk(inverted, env, impact) == PRINTED[6 - env][impact - 1]


def test_internet_attack_on_safety_function_is_very_high_when_inverted(tr) -> None:  # type: ignore[no-untyped-def]
    worst = Assessment(interface="external_network", access="non_restricted", user="layman")
    e = exposure(tr, worst)
    assert e == 5
    assert risk(tr, e, 5) == 5  # inverted (default): very high
    assert PRINTED[5][4] == 3  # literal reading would only say "moderate"


@pytest.mark.parametrize(
    "i,a,u", list(itertools.product(FACTORS["interface"], FACTORS["access"], FACTORS["user"]))
)
def test_exposure_matches_formula_for_all_combinations(tr, i: str, a: str, u: str) -> None:  # type: ignore[no-untyped-def]
    product = (
        Decimal(FACTORS["interface"][i])
        * Decimal(FACTORS["access"][a])
        * Decimal(FACTORS["user"][u])
    )
    expected = int((1 + product * 4).to_integral_value(rounding="ROUND_HALF_UP"))
    assert exposure(tr, Assessment(interface=i, access=a, user=u)) == expected
    assert 1 <= expected <= 5


def test_exposure_incomplete_is_none(tr) -> None:  # type: ignore[no-untyped-def]
    assert exposure(tr, Assessment(interface="local", access="restricted")) is None


def test_commercial_rounding() -> None:
    assert [round_half_up(Decimal(x)) for x in ("1.5", "2.5", "2.49", "3.5")] == [2, 3, 2, 4]


def threat(**kw) -> Threat:  # type: ignore[no-untyped-def]
    return Threat(id="T-0001", title="t", **kw)


def test_default_acceptance_up_to_low(tr) -> None:  # type: ignore[no-untyped-def]
    cfg = ProjectConfig(name="t")
    low = threat(
        assessment=Assessment(
            interface="physical", access="restricted", user="non_user_related", impact=4
        )
    )
    ev = evaluate(tr, low, cfg)
    assert (ev.exposure, ev.risk, ev.acceptable) == (2, 3, False)
    small = low.model_copy(update={"assessment": low.assessment.model_copy(update={"impact": 2})})
    assert evaluate(tr, small, cfg).acceptable is True


def test_rules_post_market_safety_and_fleet(tmp_path: Path) -> None:
    rules = """
acceptance:
  rules:
    - {id: post-market, label: {de: x, en: x}, enabled: true,
       when: {project.lifecycle: post_market}, max_acceptable_risk: 3}
    - {id: safety, label: {de: x, en: x}, enabled: true,
       when: {threat.safety_related: true}, max_acceptable_risk: 1}
    - {id: fleet, label: {de: x, en: x}, enabled: true,
       when: {threat.custom.fleet_wide: true}, impact_delta: 1}
"""
    method, _ = method_for(tmp_path, rules)
    a = Assessment(interface="physical", access="restricted", user="non_user_related", impact=4)
    post = ProjectConfig(name="t", lifecycle="post_market")
    assert evaluate(method, threat(assessment=a), post).acceptable is True  # risk 3 <= 3
    ev = evaluate(method, threat(assessment=a, safety_related=True), post)
    assert (ev.max_acceptable_risk, ev.rules) == (1, ["post-market", "safety"])  # strictest wins
    fleet = threat(assessment=a.model_copy(update={"impact": 5}), custom={"fleet_wide": True})
    assert evaluate(method, fleet, post).impact == 5  # clamped to the scale


def test_security_asset_inherits_and_amplifier_rounds(tr) -> None:  # type: ignore[no-untyped-def]
    assets = {
        "A-0001": Asset(id="A-0001", title="safety", asset_class="Functions.Safety"),
        "A-0002": Asset(
            id="A-0002",
            title="config",
            asset_class="Other.Configuration",
            amplifier=CiaAmplifier(i=1.5, rationale="no safe speed monitoring"),
        ),
        "A-0003": Asset(
            id="A-0003", title="key", asset_class="Security.Secrets", protects=["A-0001", "A-0002"]
        ),
        "A-0004": Asset(
            id="A-0004", title="loop", asset_class="Security.Mechanism", protects=["A-0004"]
        ),
    }
    assert asset_impact(tr, assets, "A-0002") == {"C": 1, "I": 5, "A": 1}  # 3 * 1.5 = 4.5 -> 5
    assert asset_impact(tr, assets, "A-0003") == {"C": 5, "I": 5, "A": 5}
    assert asset_impact(tr, assets, "A-0004") == {"C": None, "I": None, "A": None}
    t = threat(stride=["D"], assets=["A-0001", "A-0002"])
    s = suggest_impact(tr, t, assets)
    assert s is not None and (s.impact, s.asset_id, s.dimension) == (5, "A-0001", "A")


def test_project_method_folder_and_invalid_ids(tmp_path: Path) -> None:
    with pytest.raises(MethodError):
        load_method(tmp_path, ProjectConfig(name="t", method="../../etc"))
    with pytest.raises(MethodError):
        load_method(tmp_path, ProjectConfig(name="t", method="missing"))
    with pytest.raises(MethodError, match="risk_matrix"):
        method_for(tmp_path, "risk_matrix: {rows: {1: [1, 2]}}")
