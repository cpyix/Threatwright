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
        {"path": "machine-a", "name": "Test fixture project"}  # name from threatwright.yaml
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
    assert outside.status_code == 403


def test_server_features_are_off_locally(project_dir: Path) -> None:
    app = create_app(None, project_dir)
    c = TestClient(app, base_url="http://127.0.0.1", headers={API_HEADER: "1"})
    assert c.get("/api/app").json()["server"] is False
    assert c.get("/api/workspace").status_code == 501
    assert c.post("/api/project/upload?folder=x", content=b"").status_code == 501
    assert c.get("/api/project/download").status_code == 200  # works locally too
