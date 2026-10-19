from pathlib import Path

import pytest

from threatwright.arc import (
    ArcOverride,
    ControlApplicability,
    applicability,
    load_overrides,
    normalize,
    risk_scenarios,
    set_override,
)
from threatwright.library import I18n, MeasureTemplate, load_libraries
from threatwright.model.store import Project
from threatwright.oscal.imports import import_catalog

CATALOG = Path(__file__).parent / "fixtures" / "oscal" / "synthetic-arc-catalog.json"


def run(project_dir: Path, combined: bool = False) -> dict[str, ControlApplicability]:
    lib = import_catalog(project_dir, CATALOG)
    libs = load_libraries([lib.name], project_dir)
    project = Project.load(project_dir)
    return {r.measure_id: r for r in applicability(project, "main", libs, combined)}


def test_applicability_per_part(project_dir: Path) -> None:
    res = run(project_dir)
    # only controls with risk scenarios are evaluated
    assert sorted(res) == ["arc-1", "arc-2", "arc-3", "arc-4"]

    # field element (public restricted) handles process data with I=2
    assert res["arc-1"].applies and res["arc-1"].part == "E-0002 Remote I/O module"
    assert res["arc-1"].scenario == 1 and res["arc-1"].control_id == "ARC-1"
    assert "A-0002" in res["arc-1"].rationale["en"] and "§6.2" in res["arc-1"].rationale["de"]

    # no external network, no layman: not applicable, with the reason
    arc2 = res["arc-2"]
    assert not arc2.applies and arc2.part is None
    assert "external_network" in arc2.rationale["en"] and "layman" in arc2.rationale["en"]
    assert "C≥3 oder I≥3 oder A≥3" in arc2.rationale["de"]

    # the safety asset (A=5) is not handled by any element: not applicable per part
    assert not res["arc-3"].applies

    # no asset condition, user non_user_related matches the controller zone
    assert res["arc-4"].applies and res["arc-4"].part == "E-0001 Controller"


def test_combined_profile(project_dir: Path) -> None:
    """§6.3: highest impact of all assets combined with all environments."""
    res = run(project_dir, combined=True)
    assert res["arc-3"].applies and res["arc-3"].part == "combined"
    assert "A-0001" in res["arc-3"].rationale["en"]
    assert not res["arc-2"].applies


def test_override(project_dir: Path) -> None:
    set_override(
        project_dir,
        "main",
        "arc-2",
        ArcOverride(applies=True, rationale="Remote access planned", by="QA"),
    )
    res = run(project_dir)
    assert res["arc-2"].applies and res["arc-2"].overridden
    assert res["arc-2"].rationale["en"] == "Manual override (QA): Remote access planned"
    assert not res["arc-1"].overridden
    set_override(project_dir, "main", "arc-2", None)
    assert load_overrides(project_dir).models == {}
    assert not run(project_dir)["arc-2"].applies


def test_override_file_keeps_comments(project_dir: Path) -> None:
    path = project_dir / "profiles" / "arc-overrides.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("# decisions of the review board\nschema_version: 1\n", encoding="utf-8")
    set_override(project_dir, "main", "arc-3", ArcOverride(applies=False, rationale="n/a"))
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# decisions of the review board")
    assert load_overrides(project_dir).models["main"]["arc-3"].applies is False


def test_scenarios_from_hand_written_library_entry() -> None:
    entry = MeasureTemplate(
        id="x",
        title=I18n(de="x", en="x"),
        description=I18n(de="x", en="x"),
        kind="technical",
        oscal_extra={
            "parts": [
                {
                    "name": "statement",
                    "parts": [
                        {
                            "name": "risk-scenario",
                            "prose": "nested",
                            "props": [
                                {"name": "asset-impact", "value": "C:4"},
                                {"name": "asset-impact", "value": "bogus"},
                                {"name": "asset-class", "value": "PII.Generic"},
                                {"name": "interface-restriction", "value": "Known network"},
                                {"name": "interface-restriction", "value": "External network"},
                            ],
                        }
                    ],
                }
            ]
        },
    )
    (s,) = risk_scenarios(entry)
    assert s.impact == {"C": 4}
    assert s.asset_classes == ["PII.Generic"]
    assert s.environment == {"interface": ["known_network", "external_network"]}


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("External network", "external_network"),
        ("Non-user-related", "non_user_related"),
        (" * ", "*"),
    ],
)
def test_normalize(raw: str, key: str) -> None:
    assert normalize(raw) == key
