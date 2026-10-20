"""GUI end-to-end: a new project runs through the setup wizard to a first saved model."""

import re
from pathlib import Path

from playwright.sync_api import Page, expect


def test_setup_wizard(gui: str, page: Page, offline: list[str], tmp_path: Path) -> None:
    target = tmp_path / "neu"
    page.goto(gui)
    page.get_by_role("button", name="Start", exact=True).click()
    page.get_by_test_id("new-path").fill(str(target))
    page.get_by_test_id("new-name").fill("Testanlage")
    page.get_by_test_id("create-project").click()

    expect(page.get_by_test_id("setup")).to_be_visible()
    page.get_by_test_id("setup-start").click()

    # 1 product
    page.get_by_test_id("setup-description").fill("Zweck: Testanlage zum Verpacken.")
    page.get_by_test_id("setup-next").click()

    # 2 zones: complete the plant network zone
    page.get_by_test_id("zone-Z-PLANT-access").select_option("restricted")
    expect(page.get_by_test_id("setup-zone-Z-PLANT")).to_contain_text("bekannter Personenkreis")
    page.get_by_test_id("setup-next").click()

    # 3 components
    page.get_by_test_id("setup-type-plc").click()
    page.get_by_test_id("setup-el-title").fill("Hauptsteuerung")
    page.get_by_test_id("setup-el-add").click()
    expect(page.get_by_text("E-0001")).to_be_visible()
    page.get_by_test_id("setup-type-hmi").click()
    page.get_by_test_id("setup-el-add").click()
    expect(page.get_by_text("E-0002")).to_be_visible()
    page.get_by_test_id("setup-next").click()

    # 4 connections
    page.get_by_test_id("setup-flow-source").select_option("E-0002")
    page.get_by_test_id("setup-flow-target").select_option("E-0001")
    page.get_by_test_id("setup-flow-add").click()
    expect(page.get_by_text("F-0001")).to_be_visible()
    page.get_by_test_id("setup-next").click()

    # 5 assets: the PLC brought its typical assets; add an own one
    expect(page.get_by_text("Steuerungsprogramm (Hauptsteuerung)")).to_be_visible()
    page.get_by_test_id("setup-asset-title").fill("Rezepturen")
    page.get_by_test_id("setup-asset-class").select_option("BusinessData.Important")
    page.get_by_test_id("setup-asset-add").click()
    expect(page.get_by_role("cell", name=re.compile(r"^A-\d+ Rezepturen$"))).to_be_visible()
    page.get_by_test_id("setup-next").click()

    # 6 threats: adopt all suggestions for the PLC, answer rule 3.3
    page.get_by_test_id("setup-target-E-0001").locator("summary").click()
    page.get_by_role("button", name="alle auswählen").click()
    page.get_by_test_id("setup-adopt-E-0001").click()
    page.get_by_test_id("setup-cyber-all").click()
    expect(page.get_by_test_id("setup-cyber-all")).to_have_count(0)
    page.get_by_test_id("setup-next").click()

    # 7 finish
    checks = page.get_by_test_id("setup-checks")
    expect(checks).to_contain_text("Komponenten angelegt: 2")
    expect(checks).to_contain_text("✓ Ursachenfrage beantwortet")
    page.get_by_test_id("setup-save").click()
    expect(page.get_by_test_id("toast")).to_contain_text("Gespeichert", timeout=15_000)

    model = target / "models" / "main"
    assert "Testanlage zum Verpacken" in (model / "model.yaml").read_text(encoding="utf-8")
    assert (model / "elements" / "E-0002.yaml").exists()
    assert (model / "flows" / "F-0001.yaml").exists()
    threats = list((model / "threats").glob("T-*.yaml"))
    assert threats and all("cyber_cause: true" in t.read_text(encoding="utf-8") for t in threats)
    assert offline == [], f"unexpected outbound requests: {offline}"
