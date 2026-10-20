"""The landing view after loading must not override where the user navigated meanwhile."""

import time

from playwright.sync_api import Page, Route, expect


def test_slow_initial_load_keeps_user_navigation(gui: str, page: Page) -> None:
    delayed: list[str] = []

    def slow_first(route: Route) -> None:
        if not delayed:  # only the initial load, not later ones
            delayed.append(route.request.url)
            time.sleep(2)
        route.continue_()

    page.route("**/api/catalog/cra", slow_first)
    page.goto(gui)
    page.get_by_test_id("nav-start").click()  # project info is there, the load still runs
    page.wait_for_timeout(2500)  # initial load has finished by now
    expect(page.get_by_test_id("create-project")).to_be_visible()
    assert delayed


def test_landing_view_is_diagram_for_a_model_with_elements(gui: str, page: Page) -> None:
    page.goto(gui)
    expect(page.get_by_test_id("nav-diagram")).to_have_attribute("aria-current", "page")
