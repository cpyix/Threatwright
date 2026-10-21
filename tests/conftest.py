import asyncio
import ipaddress
import os
import shutil
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
import uvicorn
from playwright.sync_api import Page, Request, Route

from threatwright.server import WEB_DIR, create_app

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "project"

_real_connect = socket.socket.connect


def _guarded_connect(self: socket.socket, address: object) -> None:
    host = address[0] if isinstance(address, tuple) else None
    if host is not None and host != "localhost":
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            raise RuntimeError(f"outbound network access attempted: {address!r}")
    _real_connect(self, address)  # type: ignore[arg-type]


# Texts the E2E tests assert, per UI language. The UI language follows the browser
# locale, so every GUI test runs once in German and once in English.
UI_TEXT = {
    "de": {
        "saved": "Gespeichert",
        "validation": "Prüfung",
        "known_group": "bekannter Personenkreis",
        "control_program": "Steuerungsprogramm",
        "generic_connection": "allgemeine Verbindung",
        "components_added": "Komponenten angelegt",
        "cause_answered": "Ursachenfrage beantwortet",
        "configurations_info": "Varianten desselben Produkts",
    },
    "en": {
        "saved": "Saved",
        "validation": "Validation",
        "known_group": "known group of people",
        "control_program": "Control program",
        "generic_connection": "generic connection",
        "components_added": "Components added",
        "cause_answered": "Cause question answered",
        "configurations_info": "Variants of the same product",
    },
}


@pytest.fixture(params=["de", "en"])
def ui_lang(request: pytest.FixtureRequest) -> str:
    return str(request.param)


@pytest.fixture
def browser_context_args(
    browser_context_args: dict[str, object], ui_lang: str
) -> dict[str, object]:
    return {**browser_context_args, "locale": "de-DE" if ui_lang == "de" else "en-GB"}


@pytest.fixture
def ui(ui_lang: str) -> dict[str, str]:
    return UI_TEXT[ui_lang]


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-0007: the tool must never open outbound connections."""
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Writable copy of the fixture project in a path with spaces and umlauts."""
    target = tmp_path / "Projekt mit Ümlaut" / "project"
    shutil.copytree(FIXTURE, target)
    return target


# --- GUI end-to-end (tests/e2e): real server + built frontend ----------------------


def _serve(project: Path | None, root: Path | None = None) -> Iterator[str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    app = create_app(port, project, root=root)
    # THREATWRIGHT_E2E_DELAY_MS=300 slows every API answer, like a busy CI runner, so tests
    # that do not wait for the app show their races locally too
    delay = int(os.environ.get("THREATWRIGHT_E2E_DELAY_MS", "0")) / 1000
    if delay:

        @app.middleware("http")
        async def slow(request: Any, call_next: Any) -> Any:
            if request.url.path.startswith("/api/"):
                await asyncio.sleep(delay)
            return await call_next(request)

    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/"
    server.should_exit = True
    thread.join(5)


def _set_language(project: Path, lang: str) -> None:
    """An open project fixes the UI language, so each GUI run gets a project in its language."""
    config = project / "threatwright.yaml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("language: de", f"language: {lang}"),
        encoding="utf-8",
    )


@pytest.fixture
def gui(
    project_dir: Path, ui_lang: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[str]:
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "config"))
    _set_language(project_dir, ui_lang)
    yield from _serve(project_dir)


@pytest.fixture
def workspace(project_dir: Path, ui_lang: str, tmp_path: Path) -> Path:
    """Server workspace holding one project, 'machine-a'."""
    ws = tmp_path / "workspace"
    shutil.copytree(project_dir, ws / "machine-a")
    _set_language(ws / "machine-a", ui_lang)
    return ws


@pytest.fixture
def server_gui(workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """GUI in server mode (ADR-0013): no project open, workspace confined."""
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "config"))
    yield from _serve(None, root=workspace)


class AppIdle:
    """Waits for the app instead of for the clock: every click starts API requests whose
    answers re-render the page, and the next step must not overtake them."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.pending: set[Request] = set()
        page.on("request", self._started)
        page.on("requestfinished", lambda r: self.pending.discard(r))  # handlers: functions
        page.on("requestfailed", lambda r: self.pending.discard(r))
        # a reload drops the old page's requests, which may never report back
        page.on("framenavigated", lambda f: f == page.main_frame and self.pending.clear())

    def _started(self, request: Request) -> None:
        if urlparse(request.url).path.startswith("/api/"):
            self.pending.add(request)

    @property
    def open(self) -> int:
        return len(self.pending)

    def settle(self, timeout: float = 20) -> None:
        """Return once no API request has been open for 300 ms."""
        deadline = time.monotonic() + timeout
        quiet = 0
        while quiet < 3:
            if time.monotonic() > deadline:
                raise TimeoutError(f"{self.open} API request(s) still open")
            self.page.wait_for_timeout(100)  # lets Playwright deliver the request events
            quiet = quiet + 1 if self.open == 0 else 0

    def save(self) -> None:
        """Ctrl+S after all pending edits arrived, and wait until the files are written."""
        self.settle()
        with self.page.expect_response(
            lambda r: urlparse(r.url).path == "/api/save" and r.request.method == "POST",
            timeout=20_000,
        ):
            self.page.keyboard.press("Control+s")
        self.settle()


@pytest.fixture
def idle(page: Page) -> AppIdle:
    return AppIdle(page)


@pytest.fixture
def offline(page: Page) -> list[str]:
    """Abort and record every browser request that does not go to 127.0.0.1."""
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
    if (WEB_DIR / "index.html").exists():
        return
    skip = pytest.mark.skip(reason="frontend not built (npm run build in app/)")
    for item in items:
        if "e2e" in item.path.parts:
            item.add_marker(skip)
