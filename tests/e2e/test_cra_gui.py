"""GUI: CRA Annex I requirements, marking one as not applicable with a rationale."""

from pathlib import Path

from conftest import AppIdle
from playwright.sync_api import Page, expect


def test_mark_requirement_not_applicable(
    gui: str, page: Page, idle: AppIdle, offline: list[str], project_dir: Path
) -> None:
    page.goto(gui)
    page.get_by_test_id("nav-cra").click()
    row = page.get_by_test_id("cra-AI-I-2-m")
    row.get_by_test_id("cra-na-AI-I-2-m").click()
    row.get_by_test_id("cra-why").fill("No user data on the device.")
    row.locator("button[type=submit]").click()
    expect(row).to_contain_text("No user data on the device.")
    idle.save()
    text = (project_dir / "models/main/model.yaml").read_text(encoding="utf-8")
    assert "AI-I-2-m: No user data on the device." in text
    assert offline == [], f"unexpected outbound requests: {offline}"
