"""Diagram tools: connection type filter, search, multiple selection with alignment, notes."""

import re
from pathlib import Path

from conftest import AppIdle
from playwright.sync_api import Page, expect

from threatwright.model.store import Project


def test_filter_search_arrange_notes(
    ui: dict[str, str], gui: str, page: Page, idle: AppIdle, project_dir: Path
) -> None:
    page.goto(gui)
    page.get_by_test_id("nav-diagram").click()
    expect(page.get_by_test_id("node-E-0003")).to_be_visible()

    # the only connection (E-0001 -> E-0002) is untyped; E-0003 has none and disappears
    filt = page.get_by_test_id("flow-filter")
    filt.locator("summary").click()
    page.get_by_test_id("flow-filter-generic").check()
    expect(page.get_by_test_id("node-E-0003")).to_be_hidden()
    expect(page.get_by_test_id("node-E-0002")).to_be_visible()
    page.get_by_test_id("flow-filter-generic").uncheck()
    filt.locator("summary").click()
    expect(page.get_by_test_id("node-E-0003")).to_be_visible()

    page.get_by_test_id("diagram-search").fill("remote")
    expect(page.get_by_test_id("search-hits")).to_contain_text("1")
    expect(page.locator(".svelte-flow__node[data-id=E-0001]")).to_have_class(
        re.compile(r"\bdimmed\b")
    )
    page.get_by_test_id("diagram-search").fill("")

    # E-0002 (y 120) and E-0003 (y 320): align their top edges
    page.get_by_test_id("node-E-0002").click()
    page.get_by_test_id("node-E-0003").click(modifiers=["ControlOrMeta"])
    expect(page.get_by_test_id("arrange")).to_contain_text("2")
    page.get_by_test_id("arrange-top").click()
    idle.settle()  # layout is saved and the canvas rebuilt
    a = page.get_by_test_id("node-E-0002").bounding_box()
    b = page.get_by_test_id("node-E-0003").bounding_box()
    assert a and b and abs(a["y"] - b["y"]) < 1

    page.get_by_test_id("add-note").click()
    page.get_by_test_id("note-input").fill("Wartungszugang\nnur vor Ort")
    page.get_by_test_id("note-input").press("ControlOrMeta+Enter")
    expect(page.get_by_test_id("note-N1")).to_contain_text("nur vor Ort")

    idle.save()
    expect(page.get_by_test_id("toast")).to_contain_text(ui["saved"], timeout=15_000)
    layout = Project.load(project_dir).models["main"].layout
    assert layout.nodes["E-0002"].y == layout.nodes["E-0003"].y == 120
    assert layout.notes["N1"].text == "Wartungszugang\nnur vor Ort"
