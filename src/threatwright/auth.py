"""HTTP Basic Auth in front of the GUI in server mode (ADR-0013, secure by default).

Passwords are stored as PBKDF2-SHA256 hashes (`threatwright hash-password`). A
verified Authorization header is cached in memory, so the slow hash runs once
per client and password, not on every request.
"""

import base64
import binascii
import hashlib
import hmac
import os
import secrets
from collections.abc import Mapping
from pathlib import Path

ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-HMAC-SHA256
SCHEME = "pbkdf2_sha256"
DEFAULT_USER = "admin"
# folder in the workspace for a generated login; ignores itself in Git, never logged
STATE_DIR = ".threatwright"
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
    users_file: Path | None, env: Mapping[str, str], state_dir: Path
) -> tuple[dict[str, str], Path | None]:
    """Users file, else THREATWRIGHT_USER/THREATWRIGHT_PASSWORD, else a generated password.

    A generated password is stored in `state_dir/.threatwright/password` (owner-only,
    folder ignored by Git) and reused on later starts; it is never logged. Returns the
    users and that file when it is used, so the caller can point to it.
    """
    if users_file is not None:
        return load_users(users_file), None
    name = env.get("THREATWRIGHT_USER") or DEFAULT_USER
    password = env.get("THREATWRIGHT_PASSWORD")
    if password:
        return {name: hash_password(password)}, None
    folder = state_dir / STATE_DIR
    if not folder.exists():
        folder.mkdir()
        (folder / ".gitignore").write_text("*\n", encoding="utf-8")  # never committed
    stored = folder / "password"
    if not stored.exists():
        fd = os.open(stored, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(secrets.token_urlsafe(18) + "\n")
    return {name: hash_password(stored.read_text(encoding="utf-8").strip())}, stored


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
