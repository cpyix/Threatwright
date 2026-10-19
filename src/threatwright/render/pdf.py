"""PDF via a locally installed LibreOffice (optional, ADR-0007: nothing is downloaded)."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT = 180


class PdfError(Exception):
    pass


def find_soffice() -> Path | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return Path(found)
    if sys.platform == "win32":
        for env in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            base = os.environ.get(env)
            if not base:
                continue
            for candidate in sorted(Path(base).glob("LibreOffice*/program/soffice.exe")):
                if candidate.is_file():
                    return candidate
    return None


def convert(source: Path, target: Path, timeout: int = TIMEOUT) -> None:
    soffice = find_soffice()
    if soffice is None:
        raise PdfError(
            "PDF output needs LibreOffice, which was not found (looked for soffice/libreoffice "
            "on PATH and in Program Files). Install LibreOffice or build DOCX/ODT instead."
        )
    with tempfile.TemporaryDirectory(prefix="tw-pdf-") as tmp:
        profile = (Path(tmp) / "profile").as_uri()
        outdir = Path(tmp) / "out"
        cmd = [
            str(soffice),
            f"-env:UserInstallation={profile}",
            "--headless",
            "--norestore",
            "--nolockcheck",
            "--convert-to",
            "pdf",
            "--outdir",
            str(outdir),
            str(source),
        ]
        try:
            # Fixed executable and arguments, no shell.
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)  # noqa: S603
        except subprocess.TimeoutExpired as exc:
            raise PdfError(f"LibreOffice did not finish within {timeout} s") from exc
        except (subprocess.CalledProcessError, OSError) as exc:
            raise PdfError(f"LibreOffice conversion failed: {exc}") from exc
        produced = outdir / f"{source.stem}.pdf"
        if not produced.exists():
            raise PdfError(f"LibreOffice produced no PDF for {source.name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(produced), target)
