"""Add the compatibility sample of this release to tests/fixtures/compat (ADR-0015).

Run once per release, before tagging:  uv run python scripts/compat_snapshot.py
It builds the neutral demo model (the one from the screenshots) with this release
and stores the project files under tests/fixtures/compat/v<version>/. From then on
CI checks that every later release still opens, validates, saves and renders it.
"""

import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from threatwright import __version__
from threatwright.history import HISTORY_DIR
from threatwright.scaffold import create_project
from threatwright.server import TOKEN_HEADER, create_app

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "tests" / "fixtures" / "compat" / f"v{__version__}"


def main() -> None:
    spec = importlib.util.spec_from_file_location(
        "screenshots", ROOT / "scripts" / "screenshots.py"
    )
    assert spec and spec.loader
    screenshots = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(screenshots)

    if TARGET.exists():
        raise SystemExit(f"{TARGET} exists; a release's sample is never regenerated")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "demo"
        create_project(root, "tr", "Demo machine", "en")
        client = TestClient(
            create_app("t", None, root), base_url="http://127.0.0.1", headers={TOKEN_HEADER: "t"}
        )

        def call(method: str, path: str, body: object = None) -> Any:
            r = client.request(method, f"/api{path}", json=body)
            r.raise_for_status()
            return r.json()

        screenshots.build_model(call)
        shutil.copytree(root, TARGET, ignore=shutil.ignore_patterns(HISTORY_DIR, "build"))
    print(f"wrote {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
