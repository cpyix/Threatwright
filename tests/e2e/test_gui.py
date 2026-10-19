"""GUI end-to-end: create a threat, assess it, link a measure, save (M3 acceptance).

Runs against the real server and the built frontend; every request that does
not go to 127.0.0.1 is aborted and fails the test (ADR-0007).
"""

import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest
import uvicorn
from playwright.sync_api import Page, Route, expect

from threatwright.server import WEB_DIR, create_app

TOKEN = "e2e-token"
pytestmark = pytest.mark.skipif(
    not (WEB_DIR / "index.html").exists(), reason="frontend not built (npm run build in app/)"
)


@pytest.fixture
def gui(project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "config"))
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(create_app(TOKEN, port, project_dir), log_level="warning")
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/#token={TOKEN}"
    server.should_exit = True
    thread.join(5)


@pytest.fixture
def offline(page: Page) -> list[str]:
    blocked: list[str] = []

    def handle(route: Route) -> None:
        if urlparse(route.request.url).hostname == "127.0.0.1":
            route.continue_()
        else:
            blocked.append(route.request.url)
            route.abort()

    page.route("**/*", handle)
    return blocked


def test_create_assess_link_save(
    gui: str, page: Page, offline: list[str], project_dir: Path
) -> None:
    page.goto(gui)
    page.get_by_test_id("nav-threats").click()
    page.get_by_test_id("new-object").click()

    form = page.get_by_test_id("object-form")
    form.get_by_test_id("field-title").fill("Fremdes Gerät liest Prozessdaten mit")
    form.get_by_test_id("field-cyber_cause").select_option("yes")
    form.get_by_role("checkbox", name="I", exact=True).check()
    form.get_by_role("checkbox", name="E-0002 Remote I/O module").check()
    # environment is pre-filled from the zone of the target element
    expect(form.get_by_test_id("assessment-interface")).to_have_value("local")
    expect(form.get_by_test_id("assessment-access")).to_have_value("public_restricted")
    form.get_by_test_id("assessment-impact-4").click()
    panel = form.get_by_test_id("assessment-panel")
    expect(panel.get_by_test_id("risk-badge")).to_contain_text("3")
    expect(panel.get_by_test_id("assessment-verdict")).to_be_visible()

    form.get_by_role("checkbox", name="M-0001 Restrict physical access to the fieldbus").check()
    form.get_by_test_id("field-status").select_option("treated")
    form.get_by_test_id("apply").click()
    expect(form.locator("h2")).to_have_text("T-0002")

    page.keyboard.press("Control+s")
    target = project_dir / "models/main/threats/T-0002.yaml"
    expect(page.get_by_test_id("toast")).to_contain_text("Gespeichert")
    text = target.read_text(encoding="utf-8")
    assert "impact: 4" in text and "M-0001" in text and "status: treated" in text

    page.get_by_test_id("nav-validation").click()
    expect(page.get_by_role("heading", name="Prüfung")).to_be_visible()
    assert offline == [], f"unexpected outbound requests: {offline}"
