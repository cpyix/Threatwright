import ipaddress
import shutil
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

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "project"
E2E_TOKEN = "e2e-token"

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


@pytest.fixture
def gui(project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "config"))
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(create_app(E2E_TOKEN, port, project_dir), log_level="warning")
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/#token={E2E_TOKEN}"
    server.should_exit = True
    thread.join(5)


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
