"""Server mode: projects in the workspace, upload of a local project as .zip, download."""

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from threatwright import archive
from threatwright.branding import PROJECT_FILE
from threatwright.history import HISTORY_DIR
from threatwright.server import API_HEADER, create_app


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "config"))


def server(workspace: Path) -> TestClient:
    app = create_app(None, None, root=workspace)
    return TestClient(app, base_url="http://127.0.0.1", headers={API_HEADER: "1"})


def zipped(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    return buf.getvalue()


def test_workspace_open_and_new(workspace: Path) -> None:
    c = server(workspace)
    assert c.get("/api/app").json()["server"] is True
    assert c.get("/api/workspace").json()["projects"] == [
        {"path": "machine-a", "name": "Test fixture project", "archived": False}  # from the config
    ]
    assert c.post("/api/project/open", json={"path": "machine-a"}).status_code == 200
    r = c.post("/api/project/new", json={"path": "machine-b", "name": "B", "language": "en"})
    assert r.status_code == 200
    paths = [p["path"] for p in c.get("/api/workspace").json()["projects"]]
    assert paths == ["machine-a", "machine-b"]


def test_upload_local_project_and_download(workspace: Path, project_dir: Path) -> None:
    local = archive.pack(project_dir)  # e.g. zipped on the user's PC (folder inside the zip)
    c = server(workspace)
    r = c.post("/api/project/upload?folder=from-laptop", content=local)
    assert r.status_code == 200, r.text
    assert (workspace / "from-laptop" / PROJECT_FILE).is_file()
    assert c.get("/api/models/main").json()["objects"]["elements"]

    again = c.post("/api/project/upload?folder=from-laptop", content=local)
    assert again.status_code == 400 and "already exists" in again.text

    (workspace / "from-laptop" / HISTORY_DIR).mkdir()
    (workspace / "from-laptop" / HISTORY_DIR / "x.json.gz").write_bytes(b"x")
    down = c.get("/api/project/download")
    assert down.status_code == 200 and down.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(down.content)).namelist()
    assert f"from-laptop/{PROJECT_FILE}" in names
    assert not any(HISTORY_DIR in n for n in names)

    c.post("/api/models/main/measures", json={"title": "unsaved"})
    assert c.get("/api/project/download").status_code == 409


def test_upload_rejects_bad_archives(workspace: Path) -> None:
    c = server(workspace)
    assert c.post("/api/project/upload?folder=x", content=b"not a zip").status_code == 400
    no_project = zipped({"readme.txt": "hi"})
    assert c.post("/api/project/upload?folder=x", content=no_project).status_code == 400
    evil = zipped({PROJECT_FILE: "schema_version: 1\nname: x\n", "../../escape.txt": "x"})
    r = c.post("/api/project/upload?folder=y", content=evil)
    assert r.status_code == 400 and "unsafe path" in r.text
    assert not (workspace.parent / "escape.txt").exists()
    outside = c.post("/api/project/upload?folder=../elsewhere", content=no_project)
    assert outside.status_code == 400 and "inside the workspace" in outside.text


def test_server_features_are_off_locally(project_dir: Path) -> None:
    app = create_app(None, project_dir)
    c = TestClient(app, base_url="http://127.0.0.1", headers={API_HEADER: "1"})
    assert c.get("/api/app").json()["server"] is False
    assert c.get("/api/workspace").status_code == 501
    assert c.post("/api/project/upload?folder=x", content=b"").status_code == 501
    assert c.get("/api/project/download").status_code == 200  # works locally too


def test_new_project_libraries(workspace: Path) -> None:
    c = server(workspace)
    r = c.post("/api/project/new", json={"path": "dev", "libraries": ["iot"]})
    assert r.json()["config"]["libraries"] == ["iot"]
    for body in (
        {"libraries": []},
        {"libraries": ["foo"]},
        {"libraries": "iot"},
        {"name": 123},
        {"path": 5},
    ):
        body = {"path": "x", **body}
        assert c.post("/api/project/new", json=body).status_code == 422, body
        assert not (workspace / "x").exists(), body


def test_archive_search_and_delete(workspace: Path) -> None:
    c = server(workspace)
    c.post("/api/project/open", json={"path": "machine-a"})
    r = c.post("/api/projects/archive", json={"path": "machine-a", "archived": True})
    assert r.status_code == 200 and r.json()["archived"] is True
    assert "archived: true" in (workspace / "machine-a" / PROJECT_FILE).read_text("utf-8")
    assert c.get("/api/project").json()["config"]["archived"] is True  # open project reloaded
    (project,) = c.get("/api/workspace").json()["projects"]
    assert project["archived"] is True

    c.post("/api/project/new", json={"path": "machine-b"})
    assert c.delete("/api/projects?path=machine-b").status_code == 409  # not archived
    assert c.delete("/api/projects?path=../outside").status_code == 403
    assert c.delete("/api/projects?path=.").status_code == 404  # workspace is no project

    c.post("/api/project/open", json={"path": "machine-a"})
    assert c.delete("/api/projects?path=machine-a").json() == {"deleted": True}
    assert not (workspace / "machine-a").exists()
    assert c.get("/api/project").status_code == 409  # the open project was closed
    c.post("/api/projects/archive", json={"path": "machine-b", "archived": True})
    c.post("/api/projects/archive", json={"path": "machine-b", "archived": False})
    assert "archived" not in (workspace / "machine-b" / PROJECT_FILE).read_text("utf-8")


def test_archive_needs_saved_changes(workspace: Path) -> None:
    c = server(workspace)
    c.post("/api/project/open", json={"path": "machine-a"})
    c.post("/api/models/main/measures", json={"title": "unsaved"})
    r = c.post("/api/projects/archive", json={"path": "machine-a", "archived": True})
    assert r.status_code == 409
