"""UI language: without a project it follows the browser (German for German, English for
everything else); an open project fixes it to the project language."""

import pytest
from playwright.sync_api import Browser, expect


@pytest.mark.parametrize(
    ("locale", "label"), [("de-AT", "Neues Projekt"), ("fr-FR", "New project")]
)
def test_ui_language_from_browser(
    server_gui: str, browser: Browser, locale: str, label: str
) -> None:
    context = browser.new_context(locale=locale)
    page = context.new_page()
    page.goto(server_gui)
    expect(page.get_by_test_id("show-new-project")).to_contain_text(label)
    expect(page.locator("html")).to_have_attribute(
        "lang", locale[:2] if locale.startswith("de") else "en"
    )
    context.close()


def test_project_fixes_ui_language(gui: str, ui_lang: str, browser: Browser) -> None:
    # browser in the other language: the project's language wins
    context = browser.new_context(locale="en-GB" if ui_lang == "de" else "de-DE")
    page = context.new_page()
    page.goto(gui)
    expect(page.get_by_test_id("nav-diagram")).to_have_text(
        "Diagramm" if ui_lang == "de" else "Diagram"
    )
    expect(page.locator("html")).to_have_attribute("lang", ui_lang)
    expect(page.get_by_role("button", name="Sprache / language")).to_have_count(0)
    context.close()
