"""Build the portable executable and archive it.

    uv run python packaging/build.py

Needs the frontend bundle (cd app && npm ci && npm run build). PyInstaller must run inside the
project environment (it bundles what it can import), so it is added with `uv run --with`
rather than `uvx`, which would use an isolated environment without the dependencies.
Output: dist/threatwright-<version>-<os>-<arch>.zip (Windows) or .tar.gz (Linux).
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path

from threatwright import __version__

ROOT = Path(__file__).resolve().parents[1]
PYINSTALLER = "pyinstaller==6.22.3"


def main() -> None:
    if not (ROOT / "src" / "threatwright" / "web" / "index.html").exists():
        sys.exit("frontend bundle missing: cd app && npm ci && npm run build")
    uv = shutil.which("uv")
    if uv is None:
        sys.exit("uv not found: https://docs.astral.sh/uv/")
    dist = ROOT / "dist"
    subprocess.run(  # noqa: S603
        [
            uv,
            "run",
            "--with",
            PYINSTALLER,
            "pyinstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(dist),
            "--workpath",
            str(ROOT / "build" / "pyinstaller"),
            str(ROOT / "packaging" / "threatwright.spec"),
        ],
        check=True,
        cwd=ROOT,
    )
    system = platform.system().lower()
    name = f"threatwright-{__version__}-{system}-{platform.machine().lower()}"
    fmt = "zip" if system == "windows" else "gztar"
    print(shutil.make_archive(str(dist / name), fmt, dist, "threatwright"))


if __name__ == "__main__":
    main()
