"""Autosave every 30 s into the version history, restore a version from the GUI."""

from pathlib import Path

from playwright.sync_api import Page, expect

from threatwright.server import _snapshot


def add_measure(page: Page, title: str) -> None:
    page.get_by_test_id("nav-measures").click()
    page.get_by_test_id("new-object").click()
    form = page.get_by_test_id("object-form")
    form.get_by_test_id("field-title").fill(title)
    form.get_by_test_id("apply").click()
    expect(page.get_by_test_id("save")).to_contain_text("•")  # change registered as unsaved


def test_autosave_and_restore(page: Page, gui: str, project_dir: Path) -> None:
    files = _snapshot(project_dir)
    page.goto(gui)
    add_measure(page, "Autosaved measure")
    # the user switches to another window: autosave right away (otherwise every 30 s)
    page.evaluate(
        """() => {
            Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true})
            document.dispatchEvent(new Event('visibilitychange'))
            delete document.visibilityState
        }"""
    )
    expect(page.get_by_test_id("autosaved")).to_be_visible()

    add_measure(page, "Later measure")
    page.get_by_test_id("nav-history").click()
    auto = page.get_by_test_id("version-auto").first
    expect(auto).to_contain_text("2")  # two measures in that version
    auto.get_by_role("button").click()

    page.get_by_test_id("nav-measures").click()
    expect(page.get_by_role("button", name="M-0002")).to_be_visible()
    expect(page.get_by_role("button", name="M-0003")).to_have_count(0)
    assert _snapshot(project_dir) == files  # nothing written to the project files
