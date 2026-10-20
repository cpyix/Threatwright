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
    # The click must also count while /app is still pending. Delayed in the page: a sleep in a
    # route handler would block this thread and send the click only afterwards.
    page.add_init_script(
        "const f = window.fetch; window.fetch = (u, ...a) => String(u).endsWith('/api/app')"
        " ? new Promise((r) => setTimeout(r, 1000)).then(() => f(u, ...a)) : f(u, ...a)"
    )
    with page.expect_response("**/api/history"):  # the last request of the initial load
        page.goto(gui)
        page.get_by_test_id("nav-start").click()  # project info is there, the load still runs
    page.wait_for_timeout(500)  # the landing view would be applied right after it
    expect(page.get_by_test_id("create-project")).to_be_visible()
    assert delayed


def test_landing_view_is_diagram_for_a_model_with_elements(gui: str, page: Page) -> None:
    page.goto(gui)
    expect(page.get_by_test_id("nav-diagram")).to_have_attribute("aria-current", "page")
