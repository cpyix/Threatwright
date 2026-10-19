# PyInstaller spec for the portable build (ADR-0003). Run via packaging/build.py.
#
# onedir, not onefile: onefile unpacks itself into %TEMP% on every start (slow, often blocked
# or quarantined by endpoint protection on locked-down engineering PCs). onedir is shipped as a
# zip/tar.gz, unpacked anywhere without admin rights, starts fast and is inspectable.
#
# Console app: without arguments it starts the GUI in the default browser; all CLI commands
# work as usual. All package data (web bundle, methods, libraries, catalogs, document and CI
# templates, schemas) is collected from the installed package.
# ruff: noqa
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "src" / "threatwright" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    datas=collect_data_files("threatwright") + collect_data_files("docx"),
    hiddenimports=collect_submodules("threatwright") + collect_submodules("uvicorn"),
    excludes=["pytest", "playwright"],  # tkinter stays: native folder dialog
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="threatwright",
    console=True,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="threatwright", upx=False)
