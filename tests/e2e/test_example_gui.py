"""GUI: create a new project with the example model."""

from pathlib import Path

from conftest import AppIdle
from playwright.sync_api import Page, expect


def test_new_project_with_example(
    gui: str, page: Page, idle: AppIdle, offline: list[str], tmp_path: Path
) -> None:
    target = tmp_path / "example"
    page.goto(gui)
    page.get_by_test_id("nav-start").click()
    idle.settle()
    page.get_by_test_id("new-path").fill(str(target))
    page.get_by_test_id("new-lib-ot").uncheck()
    page.get_by_test_id("new-lib-software").check()
    page.get_by_test_id("new-example").check()
    page.get_by_test_id("create-project").click()
    idle.settle()
    expect(page.get_by_test_id("nav-diagram")).to_have_attribute("aria-current", "page")
    page.get_by_test_id("nav-threats").click()
    expect(page.locator("button.rowlink").first).to_have_text("T-0001")
    assert (target / "models" / "main" / "threats" / "T-0001.yaml").exists()
    assert offline == [], f"unexpected outbound requests: {offline}"
