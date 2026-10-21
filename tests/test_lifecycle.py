"""Support period (CRA Art. 13(8)) and review date of the threat model."""

import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from threatwright.model.store import Project
from threatwright.render import build_documents
from threatwright.rules import validate
from threatwright.scaffold import create_project
from threatwright.server import API_HEADER, create_app

TODAY = datetime.date(2026, 10, 21)
CODES = {"support-period-missing", "support-period-ended", "review-overdue"}


def found(project: Project) -> set[str]:
    return {i.code for i in validate(project, today=TODAY)} & CODES


def test_rules(project_dir: Path, tmp_path: Path) -> None:
    project = Project.load(project_dir)
    assert found(project) == {"support-period-missing"}  # the fixture has threats
    project.config.support_until = datetime.date(2026, 10, 20)
    project.config.next_review = datetime.date(2026, 10, 1)
    assert found(project) == {"support-period-ended", "review-overdue"}
    project.config.support_until = datetime.date(2031, 12, 31)
    project.config.next_review = TODAY
    assert found(project) == set()
    assert found(create_project(tmp_path / "new")) == set()  # nothing analysed yet


def test_settings_endpoint_and_cover(project_dir: Path) -> None:
    client = TestClient(
        create_app(None, project_dir), base_url="http://127.0.0.1", headers={API_HEADER: "1"}
    )
    body = {"lifecycle": "post_market", "support_until": "2031-12-31", "next_review": None}
    info = client.put("/api/project/settings", json=body).json()
    assert info["dirty"] and info["config"]["support_until"] == "2031-12-31"
    assert client.put("/api/project/settings", json={"lifecycle": "x"}).status_code == 422
    client.post("/api/save")
    text = (project_dir / "threatwright.yaml").read_text(encoding="utf-8")
    assert "support_until: 2031-12-31" in text and "lifecycle: post_market" in text
    (doc,) = build_documents(project_dir, "main", "tr-analysis", "md")
    assert "31. Dezember 2031" in doc.read_text("utf-8")
