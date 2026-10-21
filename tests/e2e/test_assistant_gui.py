"""STRIDE assistant: categories stay open, multi-select, select all, rule 3.3 per threat."""

from pathlib import Path

import pytest
from conftest import AppIdle
from playwright.sync_api import Page, expect

from threatwright.model.store import Project


@pytest.fixture
def project_dir(project_dir: Path) -> Path:
    cfg = project_dir / "threatwright.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + "libraries: [ot]\n", encoding="utf-8")
    return project_dir


def test_adopt_single_then_all(gui: str, page: Page, idle: AppIdle, project_dir: Path) -> None:
    page.goto(gui)
    # a drive from the library: its own templates (an untyped element gets every device template)
    page.request.post(
        gui + "api/models/main/add/element",
        headers={"X-Threatwright": "1"},
        data={"type": "drive"},
    )
    page.reload()
    page.get_by_test_id("nav-assistant").click()
    page.get_by_test_id("assistant-target").select_option("E-0004")

    first = page.locator("[data-testid^=adopt-]").first
    expect(first).to_be_visible()  # suggestions loaded
    open_before = page.locator("details[open]").count()
    first.click()
    idle.settle()
    expect(page.get_by_test_id("cyber-dialog")).to_be_hidden()  # rule 3.3 answered by the template
    expect(page.locator("span.ok").first).to_be_visible()  # adopted
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
    idle.settle()  # one request per adopted template
    expect(page.get_by_test_id("select-all-suggestions")).to_have_count(0)  # all adopted

    idle.save()
    threats = Project.load(project_dir).models["main"].objects["threats"].values()
    adopted = [t for t in threats if "E-0004" in t.targets and t.library_ref]
    assert len(adopted) == count + 1 and all(t.cyber_cause is True for t in adopted)
