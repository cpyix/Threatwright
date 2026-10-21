"""Diagram: zones are trust boundaries; layout keeps them apart, placement assigns them."""

from pathlib import Path

from conftest import AppIdle
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


def test_variant_filter_is_a_multi_select(gui: str, page: Page) -> None:
    page.goto(gui)
    page.get_by_test_id("nav-diagram").click()
    expect(page.get_by_test_id("node-E-0002")).to_be_visible()
    filt = page.get_by_test_id("config-filter")
    filt.locator("summary").click()
    page.get_by_test_id("config-K-A").check()
    expect(page.get_by_test_id("node-E-0002")).to_be_hidden()  # belongs to K-B only
    expect(filt.locator("summary")).to_contain_text("1")  # one element hidden
    page.get_by_test_id("config-K-B").check()
    expect(page.get_by_test_id("node-E-0002")).to_be_visible()


def test_auto_layout_and_zone_assignment(
    gui: str, page: Page, idle: AppIdle, project_dir: Path
) -> None:
    page.goto(gui)
    page.get_by_test_id("nav-diagram").click()
    idle.settle()
    page.get_by_test_id("auto-layout").click()
    expect(page.get_by_test_id("zone-Z-FIELD")).to_be_visible()
    idle.settle()  # layout is saved and the canvas rebuilt
    page.wait_for_timeout(300)  # fitView animation
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
    idle.settle()  # layout and zone change are saved one after the other
    expect(page.get_by_test_id("zone-Z-CABINET")).to_have_count(0)  # no members left

    idle.save()
    sub = Project.load(project_dir).models["main"]
    assert sub.objects["elements"]["E-0001"].zone == "Z-FIELD"
