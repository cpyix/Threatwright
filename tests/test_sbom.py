"""SBOMs (CycloneDX) and vulnerability statements (CycloneDX VEX, CSAF) as project files."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from threatwright import sbom
from threatwright.cli import app
from threatwright.model.objects import Element, Threat
from threatwright.model.store import Project
from threatwright.render import build_documents
from threatwright.rules import validate
from threatwright.server import API_HEADER, create_app

OPENSSL = "pkg:generic/openssl@3.0.1"
BUSYBOX = "pkg:generic/busybox@1.36.0"

SBOM = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.6",
    "components": [
        {"type": "library", "name": "openssl", "version": "3.0.1", "purl": OPENSSL + "?arch=arm"},
        {
            "type": "firmware",
            "name": "rootfs",
            "components": [
                {"bom-ref": "bb", "type": "library", "name": "busybox", "purl": BUSYBOX}
            ],
        },
    ],
    "vulnerabilities": [  # e.g. from a scanner, without analysis: affected
        {"id": "CVE-2024-0001", "affects": [{"ref": OPENSSL}]},
        {"id": "CVE-2024-0002", "analysis": {"state": "in_triage"}, "affects": [{"ref": "bb"}]},
    ],
}
VEX = {  # the manufacturer's statement settles the scanner finding
    "bomFormat": "CycloneDX",
    "specVersion": "1.6",
    "vulnerabilities": [
        {
            "id": "CVE-2024-0002",
            "analysis": {"state": "not_affected", "justification": "code_not_reachable"},
            "affects": [{"ref": BUSYBOX}],
        }
    ],
}
CSAF = {
    "document": {"csaf_version": "2.0", "title": "Advisory"},
    "product_tree": {
        "branches": [
            {
                "category": "vendor",
                "name": "OpenSSL",
                "branches": [
                    {
                        "category": "product_version",
                        "name": "3.0.1",
                        "product": {
                            "product_id": "P1",
                            "name": "OpenSSL 3.0.1",
                            "product_identification_helper": {"purl": OPENSSL},
                        },
                    }
                ],
            }
        ]
    },
    "vulnerabilities": [{"cve": "CVE-2024-0003", "product_status": {"known_affected": ["P1"]}}],
}


def write(project_dir: Path, rel: str, doc: object) -> None:
    path = project_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def with_sbom(project_dir: Path) -> Project:
    write(project_dir, "sbom/firmware.cdx.json", SBOM)
    write(project_dir, "vulnerabilities/vex.json", VEX)
    write(project_dir, "vulnerabilities/advisory.json", CSAF)
    project = Project.load(project_dir)
    element = project.models["main"].objects["elements"]["E-0001"]
    assert isinstance(element, Element)
    element.sbom = ["firmware.cdx.json"]
    project.save()
    return Project.load(project_dir)


def test_normalize_drops_qualifiers_and_subpath() -> None:
    assert sbom.normalize("PKG:npm/a@1?x=1#sub") == "pkg:npm/a@1"


def test_odd_documents_do_not_crash(tmp_path: Path) -> None:
    odd = [
        {"bomFormat": "CycloneDX", "components": {"x": 1}, "vulnerabilities": 5},
        {"bomFormat": "CycloneDX", "vulnerabilities": [{"id": "X", "affects": "pkg:a/b", "analysis": 1}]},
        {"document": {"csaf_version": "2.0"}, "product_tree": [1, "x", {"product_id": 3}],
         "vulnerabilities": [{"ids": ["x", 1], "product_status": {"fixed": [{}, "P"]}}]},
    ]  # fmt: skip
    for n, doc in enumerate(odd):
        path = tmp_path / f"{n}.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        assert sbom.read_statements(path, path.name) == []
    (tmp_path / "list.json").write_text("[]", encoding="utf-8")
    with pytest.raises(sbom.SbomError):
        sbom.read_sbom(tmp_path / "list.json")


def test_findings_merge_sboms_vex_and_csaf(project_dir: Path) -> None:
    project = with_sbom(project_dir)
    inv = sbom.inventory(project)
    assert inv.issues == [] and {c.purl for c in inv.sboms["firmware.cdx.json"]} == {
        OPENSSL,
        BUSYBOX,
    }
    found = {f.vuln: f for f in sbom.findings(project.models["main"], inv)}
    assert {v: f.state for v, f in found.items()} == {
        "CVE-2024-0001": "affected",
        "CVE-2024-0002": "not_affected",
        "CVE-2024-0003": "affected",
    }
    assert found["CVE-2024-0002"].detail == "code_not_reachable"
    assert found["CVE-2024-0003"].sources == ["vulnerabilities/advisory.json"]


def test_untreated_vulnerability_is_an_error_until_a_threat_lists_it(project_dir: Path) -> None:
    project = with_sbom(project_dir)
    errors = [i for i in validate(project) if i.code == "vulnerability-untreated"]
    assert sorted(i.message.split()[0] for i in errors) == ["CVE-2024-0001", "CVE-2024-0003"]
    assert {i.object_id for i in errors} == {"E-0001"}
    threat = project.models["main"].objects["threats"]["T-0001"]
    assert isinstance(threat, Threat)
    threat.vulnerabilities = ["CVE-2024-0001", "CVE-2024-0003"]
    assert [i for i in validate(project) if i.code == "vulnerability-untreated"] == []


def test_missing_and_invalid_files(project_dir: Path) -> None:
    project = with_sbom(project_dir)
    element = project.models["main"].objects["elements"]["E-0002"]
    assert isinstance(element, Element)
    element.sbom = ["gone.json"]
    (project_dir / "vulnerabilities" / "broken.json").write_text("{nope", encoding="utf-8")
    codes = {(i.code, i.object_id) for i in validate(project)}
    assert ("sbom-missing", "E-0002") in codes and ("sbom-invalid", None) in codes


def test_upload_cli_and_report(project_dir: Path) -> None:
    client = TestClient(
        create_app(None, project_dir), base_url="http://127.0.0.1", headers={API_HEADER: "1"}
    )
    r = client.post("/api/sbom/upload?name=firmware.cdx.json&kind=sbom", content=json.dumps(SBOM))
    assert r.json() == {"written": "sbom/firmware.cdx.json", "replaced": False, "count": 2}
    r = client.post("/api/sbom/upload?name=a.json&kind=vulnerabilities", content=json.dumps(CSAF))
    assert r.status_code == 200 and r.json()["count"] == 1
    assert client.post("/api/sbom/upload?name=x.txt", content=b"{}").status_code == 422
    assert client.post("/api/sbom/upload?name=x.json", content=b"{}").status_code == 422
    files = client.get("/api/sbom").json()
    assert files["sboms"] == [{"file": "firmware.cdx.json", "components": 2, "elements": []}]

    model = client.get("/api/models/main").json()
    element = next(e for e in model["objects"]["elements"] if e["id"] == "E-0001")
    client.put("/api/models/main/elements/E-0001", json={**element, "sbom": ["firmware.cdx.json"]})
    found = client.get("/api/models/main/vulnerabilities").json()
    # no VEX uploaded here: the scanner's in_triage finding stays open
    assert {f["vuln"] for f in found if f["open"]} == {f"CVE-2024-000{n}" for n in (1, 2, 3)}
    client.post("/api/save")

    result = CliRunner().invoke(app, ["vulnerabilities", str(project_dir)])
    assert result.exit_code == 1 and "3 untreated" in result.output
    (doc,) = build_documents(project_dir, "main", "tr-analysis", "md")
    text = doc.read_text("utf-8")
    assert "Bekannte Schwachstellen" in text and "CVE-2024-0003" in text
