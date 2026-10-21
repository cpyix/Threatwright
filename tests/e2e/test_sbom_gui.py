"""GUI: upload an SBOM, assign it to an element, turn a vulnerability into a threat."""

import json
import re
from pathlib import Path

from conftest import AppIdle
from playwright.sync_api import Page, expect

SBOM = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.6",
    "components": [{"name": "openssl", "purl": "pkg:generic/openssl@3.0.1"}],
    "vulnerabilities": [{"id": "CVE-2024-0001", "affects": [{"ref": "pkg:generic/openssl@3.0.1"}]}],
}


def test_sbom_to_threat(
    gui: str, page: Page, idle: AppIdle, offline: list[str], tmp_path: Path, project_dir: Path
) -> None:
    file = tmp_path / "firmware.cdx.json"
    file.write_text(json.dumps(SBOM), encoding="utf-8")
    page.goto(gui)
    page.get_by_test_id("nav-vulnerabilities").click()
    page.get_by_test_id("sbom-file").set_input_files(file)
    page.get_by_test_id("sbom-upload").click()
    idle.settle()
    expect(page.get_by_role("cell", name="firmware.cdx.json")).to_be_visible()
    assert (project_dir / "sbom" / "firmware.cdx.json").exists()

    page.get_by_test_id("nav-elements").click()
    page.get_by_role("button", name="E-0001", exact=True).click()
    form = page.get_by_test_id("object-form")
    form.get_by_role("checkbox", name="firmware.cdx.json").check()
    form.get_by_test_id("apply").click()
    idle.settle()

    page.get_by_test_id("nav-vulnerabilities").click()
    idle.settle()
    expect(page.get_by_test_id("vuln-untreated")).to_have_text(re.compile(r"^1 "))
    page.get_by_test_id("vuln-threat-CVE-2024-0001").click()
    idle.settle()
    form = page.get_by_test_id("object-form")
    expect(form.locator("h2")).to_contain_text("T-0002")
    expect(form.get_by_test_id("field-vulnerabilities")).to_have_value("CVE-2024-0001")
    page.get_by_test_id("nav-vulnerabilities").click()
    idle.settle()
    expect(page.get_by_test_id("vuln-untreated")).to_have_text(re.compile(r"^0 "))
    assert offline == [], f"unexpected outbound requests: {offline}"
