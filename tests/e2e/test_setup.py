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
    expect(page.locator("strong", has_text="E-0001")).to_be_visible()
    page.get_by_test_id("setup-type-hmi").click()
    page.get_by_test_id("setup-el-add").click()
    expect(page.locator("strong", has_text="E-0002")).to_be_visible()
    page.get_by_test_id("setup-next").click()

    # 4 connections; changing the source after a pick must not lose the target
    page.get_by_test_id("setup-flow-source").select_option("E-0001")
    page.get_by_test_id("setup-flow-source").select_option("E-0002")
    page.get_by_test_id("setup-flow-target").select_option("E-0001")
    page.get_by_test_id("setup-flow-add").click()
    expect(page.locator("strong", has_text="F-0001")).to_be_visible()
    page.get_by_test_id("setup-next").click()

    # 5 assets: the PLC brought its typical assets; add an own one
    expect(page.get_by_text("Steuerungsprogramm (Hauptsteuerung)")).to_be_visible()
    page.get_by_test_id("setup-asset-title").fill("Rezepturen")
    page.get_by_test_id("setup-asset-class").select_option("BusinessData.Important")
    page.get_by_test_id("setup-asset-add").click()
    expect(page.get_by_role("cell", name=re.compile(r"^A-\d+ Rezepturen$"))).to_be_visible()
    page.get_by_test_id("setup-next").click()

    # 6 threats: top suggestions only, then answer rule 3.3 one by one (no "all yes")
    target_box = page.get_by_test_id("setup-target-E-0001")
    target_box.locator("summary").click()
    boxes = target_box.locator("input[type=checkbox]")
    expect(boxes).to_have_count(5)
    boxes.nth(0).check()
    boxes.nth(1).check()
    page.get_by_test_id("setup-adopt-E-0001").click()
    expect(target_box.locator("summary")).to_contain_text("2/")
    yes = page.locator("[data-testid^=setup-cyber-yes-]")
    expect(yes).to_have_count(2)
    yes.first.click()
    expect(yes).to_have_count(1)
    yes.first.click()
    expect(yes).to_have_count(0)
    # the untyped connection explains why it has no suggestions
    page.get_by_test_id("setup-target-F-0001").locator("summary").click()
    expect(page.get_by_test_id("setup-target-F-0001")).to_contain_text("allgemeine Verbindung")
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
