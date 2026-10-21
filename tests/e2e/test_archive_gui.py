"""GUI: archive a project, find it again via search, delete it after confirmation."""

from pathlib import Path

from conftest import AppIdle
from playwright.sync_api import Page, expect


def test_archive_and_delete(
    gui: str, page: Page, idle: AppIdle, offline: list[str], project_dir: Path
) -> None:
    page.goto(gui)
    page.get_by_test_id("nav-start").click()
    recent = page.get_by_test_id("recent-projects")
    expect(recent).to_contain_text("Test fixture project")
    recent.get_by_test_id("archive").click()
    idle.settle()
    expect(page.get_by_test_id("recent-projects")).to_have_count(0)  # hidden until searched
    assert "archived: true" in (project_dir / "threatwright.yaml").read_text(encoding="utf-8")

    page.get_by_test_id("project-search").fill("fixture")
    expect(recent).to_contain_text("Test fixture project")
    recent.get_by_test_id("delete-project").click()
    dialog = page.get_by_test_id("delete-project-dialog")
    expect(dialog).to_be_visible()
    dialog.get_by_role("button").last.click()  # cancel keeps everything
    expect(dialog).to_be_hidden()
    assert project_dir.exists()
    recent.get_by_test_id("delete-project").click()
    dialog.get_by_test_id("delete-project-confirm").click()
    idle.settle()
    expect(page.get_by_test_id("recent-projects")).to_have_count(0)
    assert not project_dir.exists()
    assert offline == [], f"unexpected outbound requests: {offline}"
