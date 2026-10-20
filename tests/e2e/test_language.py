"""UI language follows the browser: German for German, English for everything else."""

import pytest
from playwright.sync_api import Browser, expect


@pytest.mark.parametrize(("locale", "label"), [("de-AT", "Diagramm"), ("fr-FR", "Diagram")])
def test_ui_language_from_browser(gui: str, browser: Browser, locale: str, label: str) -> None:
    context = browser.new_context(locale=locale)
    page = context.new_page()
    page.goto(gui)
    expect(page.get_by_test_id("nav-diagram")).to_have_text(label)
    expect(page.locator("html")).to_have_attribute(
        "lang", locale[:2] if locale.startswith("de") else "en"
    )
    context.close()
