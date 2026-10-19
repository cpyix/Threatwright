"""M5 end-to-end: preview a template in the GUI and build a document."""

from pathlib import Path

from playwright.sync_api import Page, expect


def test_preview_and_build(gui: str, page: Page, offline: list[str], project_dir: Path) -> None:
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(gui)
    page.get_by_test_id("nav-documents").click()
    page.get_by_test_id("template-tr-analysis").click()
    page.get_by_test_id("preview").click()
    frame = page.frame_locator("[data-testid=preview-frame]")
    expect(frame.locator("body")).to_contain_text("T-0001")
    expect(frame.locator("body")).to_contain_text("TR-03183-1")

    page.get_by_test_id("build-md").click()
    expect(page.get_by_test_id("written")).to_contain_text("main-tr-analysis.md")
    assert "T-0001" in (project_dir / "build" / "main-tr-analysis.md").read_text(encoding="utf-8")
    assert offline == [] and errors == []
