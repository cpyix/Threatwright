from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from threatwright.server import TOKEN_HEADER, create_app

TOKEN = "test-token"


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "config"))


@pytest.fixture
def client(project_dir: Path) -> TestClient:
    app = create_app(TOKEN, None, project_dir)
    return TestClient(app, base_url="http://127.0.0.1", headers={TOKEN_HEADER: TOKEN})


def test_token_host_and_security_headers(project_dir: Path) -> None:
    app = create_app(TOKEN, None, project_dir)
    no_token = TestClient(app, base_url="http://127.0.0.1")
    assert no_token.get("/api/project").status_code == 401
    wrong_host = TestClient(app, base_url="http://evil.example", headers={TOKEN_HEADER: TOKEN})
    assert wrong_host.get("/api/project").status_code == 403
    ok = TestClient(app, base_url="http://127.0.0.1", headers={TOKEN_HEADER: TOKEN})
    r = ok.get("/api/project")
    assert r.status_code == 200
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"


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
