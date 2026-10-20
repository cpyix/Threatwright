"""(i) buttons explain domain terms in place."""

from playwright.sync_api import Page, expect


def test_info_popover(ui: dict[str, str], gui: str, page: Page) -> None:
    page.goto(gui)
    page.get_by_test_id("nav-diagram").click()
    page.get_by_test_id("info-configurations").click()
    pop = page.get_by_test_id("info-pop-configurations")
    expect(pop).to_be_visible()
    expect(pop).to_contain_text(ui["configurations_info"])
    page.keyboard.press("Escape")
    expect(pop).to_be_hidden()
