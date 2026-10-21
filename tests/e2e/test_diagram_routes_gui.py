"""GUI: route of a connection: bend points, reset, moving an end to another side."""

from pathlib import Path

from playwright.sync_api import Page, expect

from threatwright.model.store import Project


def test_bend_points_reset_and_side(
    ui: dict[str, str], gui: str, page: Page, offline: list[str], project_dir: Path
) -> None:
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(gui)
    page.get_by_test_id("nav-diagram").click()
    page.locator(".svelte-flow__edge-label", has_text="Fieldbus process data").click()
    expect(page.get_by_test_id("route-tools")).to_be_visible()

    page.get_by_test_id("bend-add-F-0001-0").click()
    expect(page.get_by_test_id("bend-F-0001-0")).to_be_visible()
    bend = page.get_by_test_id("bend-F-0001-0").bounding_box()
    assert bend
    page.mouse.move(bend["x"] + 7, bend["y"] + 7)
    page.mouse.down()
    page.mouse.move(bend["x"] + 7, bend["y"] + 90, steps=6)
    page.mouse.up()
    page.keyboard.press("Control+s")
    expect(page.get_by_test_id("toast")).to_contain_text(ui["saved"], timeout=15_000)
    (point,) = Project.load(project_dir).models["main"].layout.edges["F-0001"].points
    first_y = point.y

    # move the target end to the top side of E-0002 (the connection is still selected)
    expect(page.get_by_test_id("route-tools")).to_be_visible()
    anchor = page.locator(".svelte-flow__edgeupdater-target")
    top = page.locator("[data-testid=node-E-0002] .svelte-flow__handle-top")
    anchor.hover()
    page.mouse.down()
    top.hover()
    top.hover()
    page.mouse.up()
    page.keyboard.press("Control+s")
    expect(page.get_by_test_id("toast")).to_contain_text(ui["saved"], timeout=15_000)
    route = Project.load(project_dir).models["main"].layout.edges["F-0001"]
    assert route.target_side == "top" and route.points == []  # new end, route starts over
    assert first_y > 0

    expect(page.get_by_test_id("route-tools")).to_be_visible()
    page.get_by_test_id("route-reset").click()
    page.keyboard.press("Control+s")
    expect(page.get_by_test_id("toast")).to_contain_text(ui["saved"], timeout=15_000)
    assert "F-0001" not in Project.load(project_dir).models["main"].layout.edges
    assert offline == [] and errors == []
