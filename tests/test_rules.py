import json
from pathlib import Path
from xml.etree import ElementTree as ET

from conftest import FIXTURE, ROOT
from typer.testing import CliRunner

from threatwright.cli import app
from threatwright.model.store import Project
from threatwright.rules import validate

BROKEN = ROOT / "tests" / "fixtures" / "broken"
runner = CliRunner()


def codes(path: Path, severity: str) -> set[tuple[str, str | None]]:
    return {(i.code, i.object_id) for i in validate(Project.load(path)) if i.severity == severity}


def test_valid_fixture_has_no_errors() -> None:
    assert codes(FIXTURE, "error") == set()


def test_broken_fixture_reports_every_planted_error() -> None:
    assert codes(BROKEN, "error") == {
        ("schema", None),
        ("unknown-configuration", "E-0001"),
        ("unknown-zone", "E-0001"),
        ("missing-rationale", "E-0001"),
        ("unresolved-ref", "F-0001"),
        ("unknown-asset-class", "A-0001"),
        ("security-asset-without-protects", "A-0002"),
        ("missing-rationale", "A-0002"),
        ("unresolved-text-ref", "T-0001"),
        ("custom-required", "T-0001"),
        ("incomplete-assessment", "T-0001"),
        ("threat-without-measure", "T-0001"),
        ("custom-invalid", "T-0002"),
        ("acceptance-without-rationale", "T-0002"),
        ("acceptance-not-allowed", "T-0002"),
        ("acceptance-not-authorized", "T-0002"),
        ("unknown-indicator-value", "T-0003"),
        ("rejection-without-rationale", "T-0003"),
        ("duplicate-uuid", "M-0002"),
    }
    warnings = {c for c, _ in codes(BROKEN, "warning")}
    assert {
        "custom-unknown",
        "cyber-cause-unanswered",
        "not-a-cyber-risk",
        "measure-unreferenced",
        "question-unreferenced",
        "coverage-gap",
    } <= warnings


def test_cli_exit_codes_and_strict() -> None:
    assert runner.invoke(app, ["validate", str(FIXTURE)]).exit_code == 0
    assert runner.invoke(app, ["validate", str(FIXTURE), "--strict"]).exit_code == 1  # warnings
    assert runner.invoke(app, ["validate", str(BROKEN)]).exit_code == 1
    assert runner.invoke(app, ["validate", str(ROOT / "docs")]).exit_code == 2  # not a project


def test_cli_formats_are_parseable(tmp_path: Path) -> None:
    out = runner.invoke(app, ["validate", str(BROKEN), "--format", "json"]).stdout
    assert {"severity", "code", "file", "location"} <= set(json.loads(out)[0])
    sarif = json.loads(runner.invoke(app, ["validate", str(BROKEN), "--format", "sarif"]).stdout)
    assert sarif["version"] == "2.1.0" and sarif["runs"][0]["results"]
    target = tmp_path / "report.xml"
    runner.invoke(app, ["validate", str(BROKEN), "--format", "junit", "-o", str(target)])
    suite = ET.parse(target).getroot().find("testsuite")
    assert suite is not None and int(suite.get("failures", "0")) == 19


def test_init_tr_project_is_valid_and_refuses_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "Neues Projekt"
    assert runner.invoke(app, ["init", str(target), "--name", "Testprodukt"]).exit_code == 0
    project = Project.load(target)
    assert project.config.name == "Testprodukt"
    assert [z.id for z in project.models["main"].meta.zones][0] == "Z-INTERNAL"
    assert validate(project) == []
    assert project.save() == []  # freshly created project is canonical
    assert runner.invoke(app, ["init", str(target)]).exit_code == 1
