from pathlib import Path

import pytest
from conftest import ROOT
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from threatwright.cli import app
from threatwright.library import load_libraries
from threatwright.model.store import Project
from threatwright.server import API_HEADER, create_app

OSCAL = ROOT / "tests" / "fixtures" / "oscal"
runner = CliRunner()


def test_cli_validate_and_import_activates_library(project_dir: Path) -> None:
    assert (
        runner.invoke(app, ["oscal", "validate", str(OSCAL / "grundschutz-excerpt.json")]).exit_code
        == 0
    )
    bad = project_dir / "bad.json"
    bad.write_text('{"catalog": {"uuid": "nope"}}', encoding="utf-8")
    assert runner.invoke(app, ["oscal", "validate", str(bad)]).exit_code == 1

    r = runner.invoke(
        app,
        [
            "oscal",
            "import",
            str(OSCAL / "grundschutz-excerpt.json"),
            "--as",
            "catalog",
            "--path",
            str(project_dir),
        ],
    )
    assert r.exit_code == 0, r.output
    project = Project.load(project_dir)
    imported = [n for n in project.config.libraries if n != "ot"]
    assert imported, project.config.libraries
    libs = load_libraries(project.config.libraries, project_dir)
    assert libs.issues == [] and libs.measures
    assert all(m.controls and m.oscal_ref for m in libs.measures.values())


def test_server_import_and_controls(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "cfg"))
    c = TestClient(
        create_app(None, project_dir), base_url="http://127.0.0.1", headers={API_HEADER: "1"}
    )
    r = c.post(
        "/api/oscal/import",
        json={"path": str(OSCAL / "synthetic-arc-catalog.json"), "as": "catalog"},
    )
    assert r.status_code == 200, r.text
    listed = c.get("/api/oscal/imported").json()
    assert listed and listed[0]["entries"] > 0
    controls = c.get("/api/models/main/controls").json()
    assert controls and {"applies", "rationale", "control_id"} <= set(controls[0])
    first = controls[0]
    after = c.put(
        f"/api/arc/main/{first['measure_id']}",
        json={"applies": not first["applies"], "rationale": "Begründung", "by": None},
    ).json()
    changed = next(x for x in after if x["measure_id"] == first["measure_id"])
    assert changed["overridden"] and changed["applies"] is not first["applies"]
    assert c.post("/api/oscal/import", json={"path": "x", "as": "nope"}).status_code == 422


def test_server_import_from_browser_upload(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The file picker uploads the file, so it also works when Threatwright runs as a server."""
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "cfg"))
    app = create_app(None, project_dir, root=project_dir.parent)
    c = TestClient(app, base_url="http://127.0.0.1", headers={API_HEADER: "1"})
    assert c.post("/api/project/open", json={"path": project_dir.name}).status_code == 200
    data = (OSCAL / "synthetic-arc-catalog.json").read_bytes()
    up = lambda name, kind="catalog": c.post(  # noqa: E731
        "/api/oscal/upload", params={"name": name, "kind": kind}, content=data
    )
    r = up("../../evil/catalog.json")  # only the base name is used, inside a temp folder
    assert r.status_code == 200, r.text
    assert c.get("/api/oscal/imported").json()[0]["entries"] > 0
    assert not (project_dir.parent.parent / "evil").exists()
    assert up("catalog.json", "nope").status_code == 422
    assert up("catalog.xml").status_code == 422  # JSON only
