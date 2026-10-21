"""GUI: route of a connection: bend points, reset, moving an end to another side."""

import time
from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import Page, expect

from threatwright.model.objects import EdgeLayout
from threatwright.model.store import Project


def saved_route(
    page: Page, project_dir: Path, done: Callable[[EdgeLayout | None], bool]
) -> EdgeLayout | None:
    """Save and wait until the file shows the route; the "saved" toast of an earlier save
    may still be visible, so the toast alone does not prove that this save is on disk."""
    deadline = time.monotonic() + 15
    while True:
        # again each round: a save pressed while the layout request was still on its way
        # writes the state before it
        page.keyboard.press("Control+s")
        page.wait_for_timeout(1000)
        route = Project.load(project_dir).models["main"].layout.edges.get("F-0001")
        if done(route) or time.monotonic() > deadline:
            return route


def test_bend_points_reset_and_side(
    gui: str, page: Page, offline: list[str], project_dir: Path
) -> None:
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(gui)
    page.get_by_test_id("nav-diagram").click()
    page.locator(".svelte-flow__edge-label", has_text="Fieldbus process data").click()
    expect(page.get_by_test_id("route-tools")).to_be_visible()

    page.get_by_test_id("bend-add-F-0001-0").click()
    bend_handle = page.get_by_test_id("bend-F-0001-0")
    expect(bend_handle).to_be_visible()
    bend = bend_handle.bounding_box()
    assert bend
    page.mouse.move(bend["x"] + 7, bend["y"] + 7)
    page.mouse.down()
    page.mouse.move(bend["x"] + 7, bend["y"] + 90, steps=6)
    page.mouse.up()
    route = saved_route(page, project_dir, lambda r: r is not None and len(r.points) == 1)
    assert route is not None and len(route.points) == 1

    # move the target end to the top side of E-0002 (the connection is still selected)
    expect(page.get_by_test_id("route-tools")).to_be_visible()
    anchor = page.locator(".svelte-flow__edgeupdater-target")
    top = page.locator("[data-testid=node-E-0002] .svelte-flow__handle-top")
    anchor.hover()
    page.mouse.down()
    top.hover()
    top.hover()
    page.mouse.up()
    expect(bend_handle).to_have_count(0)  # new end: the route starts over
    route = saved_route(page, project_dir, lambda r: r is not None and r.target_side == "top")
    assert route is not None and route.target_side == "top" and route.points == []

    expect(page.get_by_test_id("route-tools")).to_be_visible()
    page.get_by_test_id("route-reset").click()
    assert saved_route(page, project_dir, lambda r: r is None) is None
    assert offline == [] and errors == []
