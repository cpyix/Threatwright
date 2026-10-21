"""Evidence files and links on measures."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from threatwright.model.objects import Measure
from threatwright.model.store import Project
from threatwright.rules import validate
from threatwright.server import API_HEADER, create_app


@pytest.mark.parametrize(
    "ref", ["../x", "evidence/../x", "evidence/a\\b", "C:/x", "ftp://x", "evidence/", "/etc/x"]
)
def test_refs_stay_inside_evidence_or_are_links(ref: str) -> None:
    with pytest.raises(ValidationError):
        Measure(id="M-0001", title="t", evidence_refs=[ref])


def codes(project: Project) -> set[tuple[str, str]]:
    return {(i.code, i.location) for i in validate(project) if i.object_id == "M-0001"}


def test_rules(project_dir: Path) -> None:
    project = Project.load(project_dir)
    m = project.models["main"].objects["measures"]["M-0001"]
    assert isinstance(m, Measure)
    m.status, m.evidence, m.evidence_refs = "implemented", None, []
    assert ("implemented-without-evidence", "evidence") in codes(project)
    m.evidence_refs = ["https://wiki.example/test-report", "evidence/report.pdf"]
    assert codes(project) >= {("evidence-missing", "evidence_refs")}
    (project_dir / "evidence").mkdir()
    (project_dir / "evidence" / "report.pdf").write_bytes(b"%PDF")
    assert not {c for c, _ in codes(project)} & {"evidence-missing", "implemented-without-evidence"}


def test_upload_never_overwrites_and_download_is_confined(project_dir: Path) -> None:
    client = TestClient(
        create_app(None, project_dir), base_url="http://127.0.0.1", headers={API_HEADER: "1"}
    )
    first = client.post("/api/evidence/upload?name=../Prüf bericht?.pdf", content=b"one").json()
    assert first == {"ref": "evidence/Prüf bericht_.pdf"}
    second = client.post("/api/evidence/upload?name=Prüf bericht_.pdf", content=b"two").json()
    assert second == {"ref": "evidence/Prüf bericht_-2.pdf"}
    r = client.get("/api/evidence", params={"ref": first["ref"]})
    assert r.content == b"one" and r.headers["content-disposition"].startswith("attachment")
    for bad in ("threatwright.yaml", "evidence/../threatwright.yaml", "evidence/missing.pdf"):
        assert client.get("/api/evidence", params={"ref": bad}).status_code == 404
