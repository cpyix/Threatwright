"""GUI end-to-end: a new project runs through the setup wizard to a first saved model."""

import re
from pathlib import Path

from conftest import AppIdle
from playwright.sync_api import Page, expect


def test_setup_wizard(
    ui: dict[str, str], gui: str, page: Page, idle: AppIdle, offline: list[str], tmp_path: Path
) -> None:
    target = tmp_path / "neu"
    page.goto(gui)
    page.get_by_role("button", name="Start", exact=True).click()
    page.get_by_test_id("new-path").fill(str(target))
    page.get_by_test_id("new-name").fill("Testanlage")
    page.get_by_test_id("create-project").click()
    idle.settle()  # creating loads method, catalogs, library, model and validation

    expect(page.get_by_test_id("setup")).to_be_visible()
    page.get_by_test_id("setup-start").click()

    # 1 product
    page.get_by_test_id("setup-description").fill("Zweck: Testanlage zum Verpacken.")
    page.get_by_test_id("setup-next").click()

    # 2 CRA classification: optional, skipped
    expect(page.get_by_test_id("cra-result")).to_be_visible()
    page.get_by_test_id("setup-next").click()

    # 3 zones: complete the plant network zone
    page.get_by_test_id("zone-Z-PLANT-access").select_option("restricted")
    expect(page.get_by_test_id("setup-zone-Z-PLANT")).to_contain_text(ui["known_group"])
    page.get_by_test_id("setup-next").click()

    # 4 components
    page.get_by_test_id("setup-type-plc").click()
    page.get_by_test_id("setup-el-title").fill("Hauptsteuerung")
    page.get_by_test_id("setup-el-add").click()
    expect(page.locator("strong", has_text="E-0001")).to_be_visible()
    page.get_by_test_id("setup-type-hmi").click()
    page.get_by_test_id("setup-el-add").click()
    expect(page.locator("strong", has_text="E-0002")).to_be_visible()
    page.get_by_test_id("setup-next").click()

    # 5 connections; changing the source after a pick must not lose the target
    page.get_by_test_id("setup-flow-source").select_option("E-0001")
    page.get_by_test_id("setup-flow-source").select_option("E-0002")
    page.get_by_test_id("setup-flow-target").select_option("E-0001")
    page.get_by_test_id("setup-flow-add").click()
    expect(page.locator("strong", has_text="F-0001")).to_be_visible()
    page.get_by_test_id("setup-next").click()

    # 6 assets: the PLC brought its typical assets; add an own one
    expect(page.get_by_text(f"{ui['control_program']} (Hauptsteuerung)")).to_be_visible()
    page.get_by_test_id("setup-asset-title").fill("Rezepturen")
    page.get_by_test_id("setup-asset-class").select_option("BusinessData.Important")
    page.get_by_test_id("setup-asset-add").click()
    expect(page.get_by_role("cell", name=re.compile(r"^A-\d+ Rezepturen$"))).to_be_visible()
    page.get_by_test_id("setup-next").click()

    # 7 threats: top suggestions only; templates answer rule 3.3, nothing left open
    target_box = page.get_by_test_id("setup-target-E-0001")
    target_box.locator("summary").click()
    boxes = target_box.locator("input[type=checkbox]")
    expect(boxes).to_have_count(5)
    boxes.nth(0).check()
    boxes.nth(1).check()
    page.get_by_test_id("setup-adopt-E-0001").click()
    expect(target_box.locator("summary")).to_contain_text("2/")
    expect(page.locator("[data-testid^=setup-cyber-yes-]")).to_have_count(0)
    # the untyped connection explains why it has no suggestions
    page.get_by_test_id("setup-target-F-0001").locator("summary").click()
    expect(page.get_by_test_id("setup-target-F-0001")).to_contain_text(ui["generic_connection"])
    page.get_by_test_id("setup-next").click()

    # 8 finish
    checks = page.get_by_test_id("setup-checks")
    expect(checks).to_contain_text(f"{ui['components_added']}: 2")
    expect(checks).to_contain_text(f"✓ {ui['cause_answered']}")
    page.get_by_test_id("setup-save").click()
    expect(page.get_by_test_id("toast")).to_contain_text(ui["saved"], timeout=15_000)

    model = target / "models" / "main"
    assert "Testanlage zum Verpacken" in (model / "model.yaml").read_text(encoding="utf-8")
    assert (model / "elements" / "E-0002.yaml").exists()
    assert (model / "flows" / "F-0001.yaml").exists()
    threats = list((model / "threats").glob("T-*.yaml"))
    assert threats and all("cyber_cause: true" in t.read_text(encoding="utf-8") for t in threats)
    assert offline == [], f"unexpected outbound requests: {offline}"


def test_setup_product_type(
    ui: dict[str, str], gui: str, page: Page, offline: list[str], tmp_path: Path
) -> None:
    page.goto(gui)
    page.get_by_role("button", name="Start", exact=True).click()
    page.get_by_test_id("new-path").fill(str(tmp_path / "geraet"))
    page.get_by_test_id("new-lib-ot").uncheck()
    page.get_by_test_id("new-lib-iot").check()
    page.get_by_test_id("create-project").click()

    expect(page.get_by_test_id("setup")).to_be_visible()
    page.get_by_test_id("setup-start").click()
    # product step: iot questions only, no OT wording; software can be added
    page.get_by_text(re.compile("Leitfragen|Guiding questions")).click()
    expect(page.get_by_text(re.compile("Funkschnittstellen|radio interfaces"))).to_be_visible()
    expect(page.get_by_text(re.compile("Schaltschrank|control cabinet"))).to_have_count(0)
    expect(page.get_by_test_id("setup-lib-iot")).to_be_checked()
    page.get_by_test_id("setup-add-lib-software").click()
    expect(page.get_by_test_id("setup-lib-software")).to_be_checked()
    expect(page.get_by_text(re.compile("Backend|backend"))).to_be_visible()
    page.get_by_test_id("setup-next").click()  # product
    expect(page.get_by_test_id("cra-result")).to_be_visible()
    page.get_by_test_id("setup-next").click()  # CRA classification
    page.get_by_test_id("zone-Z-LAN-access").select_option("restricted")
    page.get_by_test_id("setup-next").click()  # zones
    expect(page.get_by_test_id("setup-type-iot-device")).to_be_visible()
    expect(page.get_by_test_id("setup-type-desktop-app")).to_be_visible()
    assert "libraries: [iot]" in (tmp_path / "geraet" / "threatwright.yaml").read_text(
        encoding="utf-8"
    )
