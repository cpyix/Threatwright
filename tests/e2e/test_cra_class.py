"""GUI end-to-end: the CRA classification step is orientation only and writes nothing."""

import re
from pathlib import Path

from playwright.sync_api import Page, expect

TEXT = {
    "de": (
        "Smart-Home-Produkte mit Sicherheitsfunktionen",
        "Klasse I (",
        "keine davon",
        "Standard",
    ),
    "en": ("Smart home products with security functions", "Class I (", "none of these", "Default"),
}


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_cra_class_is_orientation_only(
    ui_lang: str, ui: dict[str, str], gui: str, page: Page, offline: list[str], project_dir: Path
) -> None:
    smart_home, class_one, none, default = TEXT[ui_lang]
    before = _snapshot(project_dir)
    page.goto(gui)
    page.get_by_test_id("nav-setup").click()
    page.get_by_test_id("setup-start").click()
    page.get_by_test_id("setup-next").click()  # product -> CRA classification

    result = page.get_by_test_id("cra-result")
    page.get_by_label(smart_home).check()
    expect(result).to_contain_text(class_one)
    page.get_by_label(none, exact=True).check()
    expect(result).to_contain_text(default)
    expect(page.get_by_text(re.compile(r"Art\. 7\(4\)|Art\. 7 Abs\. 4"))).to_be_visible()

    page.get_by_test_id("setup-next").click()
    expect(page.get_by_test_id("setup-zone-Z-CABINET")).to_be_visible()
    page.keyboard.press("Control+s")
    expect(page.get_by_test_id("toast")).to_contain_text(ui["saved"], timeout=15_000)
    assert _snapshot(project_dir) == before
    assert offline == [], f"unexpected outbound requests: {offline}"
