"""Diagram: zones are trust boundaries; layout keeps them apart, placement assigns them."""

from pathlib import Path

from playwright.sync_api import Page, expect

from threatwright.model.store import Project


def _box(page: Page, testid: str) -> dict[str, float]:
    box = page.get_by_test_id(testid).bounding_box()
    assert box
    return box


def _overlap(a: dict[str, float], b: dict[str, float]) -> bool:
    return (
        a["x"] < b["x"] + b["width"]
        and b["x"] < a["x"] + a["width"]
        and a["y"] < b["y"] + b["height"]
        and b["y"] < a["y"] + a["height"]
    )


def test_auto_layout_and_zone_assignment(
    ui: dict[str, str], gui: str, page: Page, project_dir: Path
) -> None:
    page.goto(gui)
    page.get_by_test_id("nav-diagram").click()
    page.get_by_test_id("auto-layout").click()
    expect(page.get_by_test_id("zone-Z-FIELD")).to_be_visible()
    page.wait_for_timeout(500)  # layout is saved and the canvas rebuilt
    assert not _overlap(_box(page, "zone-Z-CABINET"), _box(page, "zone-Z-FIELD"))

    # move the cabinet device into the field zone
    field = _box(page, "zone-Z-FIELD")
    node = _box(page, "node-E-0001")
    page.mouse.move(node["x"] + node["width"] / 2, node["y"] + node["height"] / 2)
    page.mouse.down()
    page.mouse.move(
        field["x"] + 30 + node["width"] / 2, field["y"] + field["height"] - 30, steps=10
    )
    page.mouse.up()
    expect(page.get_by_test_id("zone-Z-CABINET")).to_have_count(0)  # no members left

    page.keyboard.press("Control+s")
    expect(page.get_by_test_id("toast")).to_contain_text(ui["saved"], timeout=15_000)
    sub = Project.load(project_dir).models["main"]
    assert sub.objects["elements"]["E-0001"].zone == "Z-FIELD"
