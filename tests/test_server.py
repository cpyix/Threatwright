import base64
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from threatwright import server
from threatwright.auth import hash_password, users_from, verify_password
from threatwright.server import API_HEADER, create_app


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "config"))


@pytest.fixture
def client(project_dir: Path) -> TestClient:
    app = create_app(None, project_dir)
    return TestClient(app, base_url="http://127.0.0.1", headers={API_HEADER: "1"})


def test_csrf_header_host_and_security_headers(project_dir: Path) -> None:
    app = create_app(None, project_dir)
    # a request another website could send: no custom header -> refused (CSRF)
    cross_site = TestClient(app, base_url="http://127.0.0.1")
    assert cross_site.post("/api/save").status_code == 403
    assert cross_site.get("/api/project").status_code == 403
    wrong_host = TestClient(app, base_url="http://evil.example", headers={API_HEADER: "1"})
    assert wrong_host.get("/api/project").status_code == 403
    ok = TestClient(app, base_url="http://127.0.0.1", headers={API_HEADER: "1"})
    r = ok.get("/api/project")
    assert r.status_code == 200
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"


def test_allowed_hosts_for_server_use(project_dir: Path) -> None:
    app = create_app(8080, project_dir, frozenset({"tw.example.com"}))

    def status(base: str) -> int:
        c = TestClient(app, base_url=base, headers={API_HEADER: "1"})
        return c.get("/api/project").status_code

    assert status("https://tw.example.com") == 200  # behind a proxy, any port
    assert status("http://tw.example.com:9000") == 200
    assert status("http://127.0.0.1:8080") == 200
    assert status("http://127.0.0.1:9000") == 403
    assert status("http://evil.example:8080") == 403


def test_server_mode_confines_client_paths(project_dir: Path, tmp_path: Path) -> None:
    app = create_app(None, project_dir, root=project_dir.parent)
    c = TestClient(app, base_url="http://127.0.0.1", headers={API_HEADER: "1"})
    outside = tmp_path / "elsewhere"
    assert c.post("/api/project/open", json={"path": str(outside)}).status_code == 403
    assert c.post("/api/project/open", json={"path": "../../.."}).status_code == 403
    assert c.post("/api/project/new", json={"path": str(outside), "name": "x"}).status_code == 403
    assert not outside.exists()
    assert c.post("/api/project/open", json={"path": project_dir.name}).status_code == 200
    assert c.post("/api/pick-folder", json={}).status_code == 501
    assert c.post("/api/open-build-folder").status_code == 501
    (project_dir / "build").mkdir(exist_ok=True)
    (project_dir / "build" / "main-x.html").write_text("doc", encoding="utf-8")
    assert c.get("/api/build/main-x.html").content == b"doc"  # downloaded instead of opened
    assert c.get("/api/build/..%2Fthreatwright.yaml").status_code == 404
    assert c.get("/api/build/missing.pdf").status_code == 404


def test_layout_notes(client: TestClient) -> None:
    note = {"x": 10, "y": 20, "text": "Hinweis"}
    put = lambda body: client.put("/api/models/main/layout", json=body)  # noqa: E731
    assert put({"nodes": {}, "notes": {"N1": note}}).status_code == 200
    assert put({"nodes": {"E-0001": {"x": 1, "y": 2}}}).status_code == 200  # keeps the notes
    layout = client.get("/api/models/main").json()["layout"]
    assert layout["notes"] == {"N1": {"x": 10.0, "y": 20.0, "text": "Hinweis"}}
    assert put({"nodes": {}, "notes": {"N1": {"x": 1}}}).status_code == 422


def test_open_build_folder_refuses_symlink(
    client: TestClient, project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[object] = []
    monkeypatch.setattr(server.subprocess, "Popen", opened.append)
    monkeypatch.setattr(server.os, "startfile", opened.append, raising=False)
    try:
        (project_dir / "build").symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks not permitted")
    assert client.post("/api/open-build-folder").status_code == 409
    assert opened == []
    (tmp_path / "secret.txt").write_text("x", encoding="utf-8")
    assert client.get("/api/build/secret.txt").status_code == 404


def test_frontend_does_not_serve_files_outside_web_dir(client: TestClient) -> None:
    leaked = client.get("/..%2Fserver.py")
    assert leaked.status_code in (200, 503) and "create_app" not in leaked.text


def test_basic_auth_guards_everything(project_dir: Path) -> None:
    users = {"alice": hash_password("correct horse battery", iterations=1000)}
    app = create_app(None, project_dir, users=users)
    anonymous = TestClient(app, base_url="http://127.0.0.1", headers={API_HEADER: "1"})
    for path in ("/", "/api/project"):
        r = anonymous.get(path)
        assert r.status_code == 401 and r.headers["www-authenticate"].startswith("Basic")

    def login(user: str, password: str) -> TestClient:
        basic = base64.b64encode(f"{user}:{password}".encode()).decode()
        headers = {API_HEADER: "1", "Authorization": f"Basic {basic}"}
        return TestClient(app, base_url="http://127.0.0.1", headers=headers)

    assert login("alice", "nope").get("/api/project").status_code == 401
    assert login("bob", "x").get("/api/project").status_code == 401
    ok = login("alice", "correct horse battery")
    assert ok.get("/api/project").status_code == 200
    assert ok.get("/api/project").status_code == 200  # cached verification


def test_users_from_file_env_or_generated(tmp_path: Path) -> None:
    line = f"carol:{hash_password('a long passphrase', iterations=1000)}\n"
    users_file = tmp_path / "users"
    users_file.write_text("# team\n" + line, encoding="utf-8")
    assert list(users_from(users_file, {}, tmp_path)[0]) == ["carol"]
    (tmp_path / "bad").write_text("carol:plaintext\n", encoding="utf-8")
    with pytest.raises(ValueError, match="name:pbkdf2"):
        users_from(tmp_path / "bad", {}, tmp_path)
    users, stored = users_from(None, {"THREATWRIGHT_PASSWORD": "secret pass"}, tmp_path)
    assert list(users) == ["admin"] and stored is None
    assert verify_password("secret pass", users["admin"])

    # secure by default: never open; a generated password goes to a file, not to the log
    users, stored = users_from(None, {}, tmp_path)
    assert stored == tmp_path / ".threatwright" / "password"
    assert (stored.parent / ".gitignore").read_text(encoding="utf-8") == "*\n"  # never committed
    password = stored.read_text(encoding="utf-8").strip()
    assert verify_password(password, users["admin"])
    again, _ = users_from(None, {}, tmp_path)  # reused on the next start
    assert verify_password(password, again["admin"])
    if os.name == "posix":
        assert stored.stat().st_mode & 0o077 == 0  # owner only


def test_server_mode_defaults_to_basic_auth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)  # the workspace defaults to the working directory
    seen: dict[str, object] = {}

    def fake_create_app(*args: object, **kwargs: object) -> object:
        seen["users"] = args[4] if len(args) > 4 else kwargs.get("users")
        raise SystemExit(0)  # stop before the server runs

    monkeypatch.setattr(server, "create_app", fake_create_app)
    monkeypatch.delenv("THREATWRIGHT_PASSWORD", raising=False)
    with pytest.raises(SystemExit):
        server.serve(None, open_browser=False, host="127.0.0.1", allowed_hosts=("tw.example",))
    assert seen["users"]  # shared -> login on
    password = (tmp_path / ".threatwright" / "password").read_text(encoding="utf-8").strip()
    assert password not in capsys.readouterr().out  # never in the log
    with pytest.raises(SystemExit):
        server.serve(None, open_browser=False)
    assert seen["users"] is None  # local GUI -> no login
    with pytest.raises(SystemExit):
        server.serve(None, open_browser=False, allowed_hosts=("tw.example",), auth="none")
    assert seen["users"] is None  # explicitly switched off


def test_create_assess_link_save_flow(client: TestClient, project_dir: Path) -> None:
    measure = client.post("/api/models/main/measures", json={"title": "Port verschließen"}).json()
    mid = measure["object"]["id"]
    assert mid == "M-0002"

    draft = {
        "title": "Fremdes Gerät am Feldbus",
        "stride": ["T"],
        "targets": ["E-0002"],
        "assets": ["A-0002"],
        "assessment": {
            "interface": "local",
            "access": "restricted",
            "user": "non_user_related",
            "impact": 4,
        },
    }
    live = client.post("/api/models/main/evaluate", json=draft).json()
    assert live["assessment"]["exposure"] == 2 and live["assessment"]["risk"] == 3
    assert live["suggestion"]["asset_id"] == "A-0002"

    created = client.post("/api/models/main/threats", json=draft).json()["object"]
    tid = created["id"]
    created["measures"] = [mid]
    created["status"] = "treated"
    created["cyber_cause"] = True
    put = client.put(f"/api/models/main/threats/{tid}", json=created)
    assert put.status_code == 200
    assert put.json()["model"]["evaluations"][tid]["assessment"]["risk"] == 3

    assert not (project_dir / f"models/main/threats/{tid}.yaml").exists()  # nothing written yet
    assert client.get("/api/project").json()["dirty"] is True
    written = client.post("/api/save").json()["written"]
    assert f"models/main/threats/{tid}.yaml" in written
    assert client.get("/api/project").json()["dirty"] is False
    assert client.post("/api/save").json()["written"] == []
    issues = client.get("/api/validate").json()
    assert not [i for i in issues if i["severity"] == "error"]


def test_invalid_input_is_rejected(client: TestClient) -> None:
    r = client.post("/api/models/main/threats", json={"title": "x", "stride": ["X"]})
    assert r.status_code == 422
    assert client.post("/api/models/main/nope", json={}).status_code == 404
    assert client.post("/api/models", json={"name": "../x"}).status_code == 422


def test_undo_redo(client: TestClient) -> None:
    client.delete("/api/models/main/questions/Q-0001")
    assert client.get("/api/project").json()["models"]["main"]["counts"]["questions"] == 0
    client.post("/api/undo")
    assert client.get("/api/project").json()["models"]["main"]["counts"]["questions"] == 1
    client.post("/api/redo")
    assert client.get("/api/project").json()["models"]["main"]["counts"]["questions"] == 0


def test_preview_url_is_single_use_with_strict_csp(client: TestClient) -> None:
    templates = client.get("/api/templates").json()
    assert {"tr-analysis", "acceptance-criteria", "tr-analysis-compact"} <= {
        t["id"] for t in templates
    }
    url = client.post("/api/preview", json={"template": "tr-analysis", "model": "main"}).json()[
        "url"
    ]
    page = client.get(url)
    assert page.status_code == 200 and "T-0001" in page.text
    assert "script-src" not in page.headers["content-security-policy"]
    assert "default-src 'none'" in page.headers["content-security-policy"]
    assert client.get(url).status_code == 404  # single use
    assert client.post("/api/build", json={"format": "exe"}).status_code == 422


def test_external_changes_are_detected(client: TestClient, project_dir: Path) -> None:
    assert client.get("/api/changes").json()["changed"] == []
    path = project_dir / "models/main/assets/A-0001.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("Safety functions", "Changed"), encoding="utf-8"
    )
    assert client.get("/api/changes").json()["changed"] == ["models/main/assets/A-0001.yaml"]
    client.post("/api/reload")
    model = client.get("/api/models/main").json()
    assert {a["title"] for a in model["objects"]["assets"]} >= {"Changed"}
    assert client.get("/api/changes").json()["changed"] == []


def test_pick_folder(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake(title: str, initial: str | None = None) -> str | None:
        calls.append((title, initial))
        return "/picked"

    monkeypatch.setattr(server, "pick_folder", fake)
    assert client.post("/api/pick-folder", json={"title": "T"}).json() == {"path": "/picked"}
    assert calls == [("T", None)]

    def headless(title: str, initial: str | None = None) -> str | None:
        raise RuntimeError("no desktop")

    monkeypatch.setattr(server, "pick_folder", headless)
    assert client.post("/api/pick-folder", json={}).status_code == 501


def test_pick_folder_macos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def run(cmd: list[str], **kwargs: object) -> object:
        calls.append(cmd)
        return type("Result", (), {"stdout": stdout})()

    monkeypatch.setattr(server.sys, "platform", "darwin")
    monkeypatch.setattr(server.subprocess, "run", run)
    stdout = f"{tmp_path}/picked/\n"
    assert server.pick_folder("T", str(tmp_path)) == str(tmp_path / "picked")
    assert calls[-1][0] == "/usr/bin/osascript"
    assert calls[-1][-2:] == ["T", str(tmp_path)]  # as argv, not inside the script
    stdout = ""  # cancelled
    assert server.pick_folder("T", str(tmp_path)) is None
