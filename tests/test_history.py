"""Autosave and version history (ADR-0014)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from threatwright import history
from threatwright.model.store import Project
from threatwright.server import API_HEADER, _snapshot, create_app


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "config"))


def client(project_dir: Path) -> TestClient:
    app = create_app(None, project_dir)
    return TestClient(app, base_url="http://127.0.0.1", headers={API_HEADER: "1"})


def measures(c: TestClient) -> list[str]:
    return [m["id"] for m in c.get("/api/models/main").json()["objects"]["measures"]]


def test_dump_load_roundtrip(project_dir: Path) -> None:
    models = Project.load(project_dir).models
    again = history.load(history.dump(models))
    assert history.dump(again) == history.dump(models)


def test_autosave_restore_and_undo(project_dir: Path) -> None:
    c = client(project_dir)
    files_before = _snapshot(project_dir)
    assert c.post("/api/autosave").json()["saved"] is False  # nothing changed yet

    c.post("/api/models/main/measures", json={"title": "First"})
    assert c.post("/api/autosave").json()["saved"] is True
    assert c.post("/api/autosave").json()["saved"] is False  # no new edits
    first = c.get("/api/history").json()["entries"][0]
    assert first["kind"] == "auto" and first["counts"]["measures"] == 2

    c.post("/api/models/main/measures", json={"title": "Second"})
    assert measures(c) == ["M-0001", "M-0002", "M-0003"]
    c.post(f"/api/history/{first['id']}/restore").raise_for_status()
    assert measures(c) == ["M-0001", "M-0002"]
    c.post("/api/undo").raise_for_status()  # restoring is an ordinary, undoable change
    assert measures(c) == ["M-0001", "M-0002", "M-0003"]

    # autosaves never touch the project files and never get committed
    assert _snapshot(project_dir) == files_before
    folder = project_dir / history.HISTORY_DIR
    assert (folder / ".gitignore").read_text(encoding="utf-8") == "*\n"


def test_unsaved_autosave_is_offered_once_after_reopening(project_dir: Path) -> None:
    c = client(project_dir)
    c.post("/api/models/main/measures", json={"title": "Not saved"})
    c.post("/api/autosave")
    auto = c.get("/api/history").json()["entries"][0]["id"]

    reopened = client(project_dir)  # e.g. browser closed, server restarted
    state = reopened.get("/api/history").json()
    assert state["pending"] == auto
    assert measures(reopened) == ["M-0001"]  # files untouched
    reopened.post(f"/api/history/{auto}/restore").raise_for_status()
    assert measures(reopened) == ["M-0001", "M-0002"]

    assert client(project_dir).get("/api/history").json()["pending"] is None


def test_save_adds_a_version_and_clears_the_offer(project_dir: Path) -> None:
    c = client(project_dir)
    c.post("/api/models/main/measures", json={"title": "Saved"})
    c.post("/api/autosave")
    c.post("/api/save").raise_for_status()
    kinds = [e["kind"] for e in c.get("/api/history").json()["entries"]]
    assert kinds[:2] == ["save", "auto"]
    assert client(project_dir).get("/api/history").json()["pending"] is None
    c.post("/api/save")  # unchanged save: no extra version
    assert len(c.get("/api/history").json()["entries"]) == 2


def test_unknown_versions_are_rejected(project_dir: Path) -> None:
    c = client(project_dir)
    assert c.post("/api/history/20990101T000000_000000-auto/restore").status_code == 404
    assert c.post("/api/history/..%2F..%2Fx/restore").status_code in (404, 405)  # no route
