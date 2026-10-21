"""GUI: route of a connection: bend points, reset, moving an end to another side."""

from pathlib import Path

from conftest import AppIdle
from playwright.sync_api import Page, expect

from threatwright.model.objects import EdgeLayout
from threatwright.model.store import Project


def route(project_dir: Path) -> EdgeLayout | None:
    return Project.load(project_dir).models["main"].layout.edges.get("F-0001")


def test_bend_points_reset_and_side(
    gui: str, page: Page, idle: AppIdle, offline: list[str], project_dir: Path
) -> None:
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(gui)
    page.get_by_test_id("nav-diagram").click()
    idle.settle()
    page.locator(".svelte-flow__edge-label", has_text="Fieldbus process data").click()
    expect(page.get_by_test_id("route-tools")).to_be_visible()

    page.get_by_test_id("bend-add-F-0001-0").click()
    idle.settle()  # the layout is saved and the diagram redrawn before the point is grabbed
    handle = page.get_by_test_id("bend-F-0001-0")
    handle.hover()
    page.mouse.down()
    box = handle.bounding_box()
    assert box
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + 90, steps=6)
    page.mouse.up()
    idle.save()
    first = route(project_dir)
    assert first is not None and len(first.points) == 1

    # move the target end to the top side of E-0002 (the connection is still selected)
    expect(page.get_by_test_id("route-tools")).to_be_visible()
    top = page.locator("[data-testid=node-E-0002] .svelte-flow__handle-top")
    page.locator(".svelte-flow__edgeupdater-target").hover()
    page.mouse.down()
    top.hover()
    top.hover()
    page.mouse.up()
    idle.settle()
    expect(handle).to_have_count(0)  # new end: the route starts over
    idle.save()
    moved = route(project_dir)
    assert moved is not None and moved.target_side == "top" and moved.points == []

    expect(page.get_by_test_id("route-tools")).to_be_visible()
    page.get_by_test_id("route-reset").click()
    idle.save()
    assert route(project_dir) is None
    assert offline == [] and errors == []
