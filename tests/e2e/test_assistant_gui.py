"""STRIDE assistant: categories stay open, multi-select, select all, rule 3.3 per threat."""

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from threatwright.model.store import Project


@pytest.fixture
def project_dir(project_dir: Path) -> Path:
    cfg = project_dir / "threatwright.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + "libraries: [ot]\n", encoding="utf-8")
    return project_dir


def test_adopt_single_then_all(gui: str, page: Page, project_dir: Path) -> None:
    page.goto(gui)
    # a drive from the library: its own templates (an untyped element gets every device template)
    token = {"X-Threatwright-Token": gui.rsplit("token=", 1)[1]}
    page.request.post(
        gui.split("#")[0] + "api/models/main/add/element", headers=token, data={"type": "drive"}
    )
    page.reload()
    page.get_by_test_id("nav-assistant").click()
    page.get_by_test_id("assistant-target").select_option("E-0004")

    first = page.locator("[data-testid^=adopt-]").first
    expect(first).to_be_visible()  # suggestions loaded
    open_before = page.locator("details[open]").count()
    first.click()
    dialog = page.get_by_test_id("cyber-dialog")  # one threat: the dialog asks rule 3.3
    dialog.get_by_test_id("cyber-yes").click()
    expect(dialog).to_be_hidden()
    expect(page.locator("details[open]")).to_have_count(open_before)  # nothing collapsed

    # pick two by hand, then take everything that is left
    boxes = page.locator("[data-testid^=choose-]")
    boxes.nth(0).check()
    boxes.nth(1).check()
    expect(page.get_by_test_id("adopt-bar")).to_contain_text("2")
    page.get_by_test_id("select-all-suggestions").click()
    remaining = page.get_by_test_id("select-all-suggestions").inner_text()
    count = int(remaining.rsplit("(", 1)[1].rstrip(")"))
    expect(page.get_by_test_id("adopt-bar")).to_contain_text(str(count))
    page.get_by_test_id("adopt-chosen").click()

    # several at once: no dialog storm, an inline list asks rule 3.3 per threat
    cyber = page.get_by_test_id("assistant-cyber")
    yes = cyber.locator("[data-testid^=cyber-yes-]")
    expect(yes).to_have_count(count)
    for left in range(count - 1, -1, -1):
        yes.first.click()
        expect(yes).to_have_count(left)
    expect(cyber).to_have_count(0)
    expect(page.get_by_test_id("select-all-suggestions")).to_have_count(0)  # all adopted

    page.keyboard.press("Control+s")
    expect(page.get_by_test_id("toast")).not_to_be_empty(timeout=15_000)
    threats = Project.load(project_dir).models["main"].objects["threats"].values()
    adopted = [t for t in threats if "E-0004" in t.targets and t.library_ref]
    assert len(adopted) == count + 1 and all(t.cyber_cause is True for t in adopted)
