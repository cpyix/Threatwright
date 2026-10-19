"""Shared fixtures for GUI end-to-end tests: real server + built frontend.

Every request that does not go to 127.0.0.1 is aborted and recorded (ADR-0007).
"""

import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest
import uvicorn
from playwright.sync_api import Page, Route

from threatwright.server import WEB_DIR, create_app

TOKEN = "e2e-token"


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


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if not (WEB_DIR / "index.html").exists():
        skip = pytest.mark.skip(reason="frontend not built (npm run build in app/)")
        for item in items:
            item.add_marker(skip)
