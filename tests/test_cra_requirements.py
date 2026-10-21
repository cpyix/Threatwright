"""Coverage of the CRA Annex I essential requirements per model."""

from pathlib import Path

from fastapi.testclient import TestClient

from threatwright.cra import annex_i, coverage
from threatwright.model.objects import Measure
from threatwright.model.store import Project
from threatwright.render import build_documents
from threatwright.rules import validate
from threatwright.scaffold import create_project
from threatwright.server import API_HEADER, create_app


def by_id(project: Project) -> dict[str, str]:
    return {r.id: r.status for r in coverage(project.models["main"])}


def test_status_follows_threats_measures_and_rationale(project_dir: Path) -> None:
    project = Project.load(project_dir)
    sub = project.models["main"]
    # the fixture threat references AI-I-2-e and has measure M-0001 (not implemented)
    assert by_id(project)["AI-I-2-e"] == "planned"
    measure = sub.objects["measures"]["M-0001"]
    assert isinstance(measure, Measure)
    measure.status = "implemented"
    assert by_id(project)["AI-I-2-e"] == "implemented"
    measure.cra_refs = ["AI-II-5"]  # a measure may address a requirement directly
    assert by_id(project)["AI-II-5"] == "implemented"
    sub.meta.cra_not_applicable = {"AI-I-2-m": "No user data on the device."}
    assert by_id(project)["AI-I-2-m"] == "not_applicable"
    assert by_id(project)["AI-I-2-g"] == "open"
    assert set(by_id(project)) == set(annex_i())


def test_rules_warn_about_open_requirements_once_threats_exist(
    project_dir: Path, tmp_path: Path
) -> None:
    project = Project.load(project_dir)
    project.models["main"].meta.cra_not_applicable = {"AI-I-2-m": "No user data.", "AI-X": " "}
    issues = validate(project)
    uncovered = {i.location for i in issues if i.code == "cra-requirement-uncovered"}
    assert "cra_not_applicable.AI-I-2-g" in uncovered
    assert "cra_not_applicable.AI-I-2-e" not in uncovered  # has a threat and a measure
    assert "cra_not_applicable.AI-I-2-m" not in uncovered  # justified
    assert {(i.code, i.location) for i in issues if i.code != "cra-requirement-uncovered"} >= {
        ("unknown-cra-ref", "cra_not_applicable.AI-X"),
        ("missing-rationale", "cra_not_applicable.AI-X"),
    }
    # a fresh project without threats gets no list of gaps
    empty = create_project(tmp_path / "new")
    assert [i for i in validate(empty) if i.code == "cra-requirement-uncovered"] == []


def test_report_and_api(project_dir: Path) -> None:
    (doc,) = build_documents(project_dir, "main", "tr-analysis", "md")
    text = doc.read_text("utf-8")
    assert "Grundlegende Anforderungen des CRA (Anhang I)" in text and "AI-II-8" in text
    client = TestClient(
        create_app(None, project_dir), base_url="http://127.0.0.1", headers={API_HEADER: "1"}
    )
    rows = client.get("/api/models/main/cra").json()
    assert {r["id"]: r["status"] for r in rows}["AI-I-2-e"] == "planned"
