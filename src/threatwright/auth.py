"""HTTP Basic Auth in front of the GUI in server mode (ADR-0013, secure by default).

Passwords are stored as PBKDF2-SHA256 hashes (`threatwright hash-password`). A
verified Authorization header is cached in memory, so the slow hash runs once
per client and password, not on every request.
"""

import base64
import binascii
import hashlib
import hmac
import secrets
from collections.abc import Mapping
from pathlib import Path

ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-HMAC-SHA256
SCHEME = "pbkdf2_sha256"
DEFAULT_USER = "admin"
REALM = 'Basic realm="Threatwright", charset="UTF-8"'


def hash_password(password: str, iterations: int = ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    b64 = base64.b64encode
    return "$".join([SCHEME, str(iterations), b64(salt).decode(), b64(digest).decode()])


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt, digest = encoded.split("$")
        if scheme != SCHEME:
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.b64decode(salt), int(iterations)
        )
    except (ValueError, binascii.Error):
        return False
    return hmac.compare_digest(actual, expected)


def load_users(path: Path) -> dict[str, str]:
    """`name:hash` per line; empty lines and # comments are ignored."""
    users = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, encoded = line.partition(":")
        if not sep or not name or not encoded.startswith(SCHEME + "$"):
            raise ValueError(f"{path}: expected 'name:{SCHEME}$…' per line")
        users[name] = encoded
    if not users:
        raise ValueError(f"{path}: no users")
    return users


def users_from(
    users_file: Path | None, env: Mapping[str, str]
) -> tuple[dict[str, str], tuple[str, str] | None]:
    """Users file, else THREATWRIGHT_USER/THREATWRIGHT_PASSWORD, else a generated password.

    Returns the users and, when a password was generated, (name, password) to print once.
    """
    if users_file is not None:
        return load_users(users_file), None
    name = env.get("THREATWRIGHT_USER") or DEFAULT_USER
    password = env.get("THREATWRIGHT_PASSWORD")
    generated = None
    if not password:
        password = secrets.token_urlsafe(18)
        generated = (name, password)
    return {name: hash_password(password)}, generated


class BasicAuth:
    def __init__(self, users: dict[str, str]) -> None:
        self.users = users
        self._ok: set[bytes] = set()  # sha256 of verified Authorization headers
        # unknown names are checked against this, so timing does not reveal valid names
        self._dummy = hash_password(secrets.token_urlsafe(16))

    def check(self, header: str | None) -> bool:
        if not header or not header.startswith("Basic "):
            return False
        key = hashlib.sha256(header.encode()).digest()
        if key in self._ok:
            return True
        try:
            name, _, password = base64.b64decode(header[6:]).decode().partition(":")
        except (binascii.Error, UnicodeDecodeError):
            return False
        encoded = self.users.get(name)
        ok = verify_password(password, encoded or self._dummy)
        if encoded is None or not ok:
            return False
        if len(self._ok) > 256:  # ponytail: bounded cache, cleared wholesale
            self._ok.clear()
        self._ok.add(key)
        return True
