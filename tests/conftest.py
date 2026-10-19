import ipaddress
import shutil
import socket
from pathlib import Path

import pytest

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
