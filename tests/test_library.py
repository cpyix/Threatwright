import itertools
import os
import shutil
from pathlib import Path

import pytest
from conftest import FIXTURE, ROOT
from typer.testing import CliRunner

from threatwright.cli import app
from threatwright.library import CATALOG_NAMES, CATALOGS, check_library_refs, load_libraries
from threatwright.method import load_method
from threatwright.model.objects import ProjectConfig
from threatwright.model.store import Project
from threatwright.rules import validate

runner = CliRunner()


# Minimum (elements, threats, measures) per bundled library.
BUNDLED = {"ot": (25, 120, 80), "iot": (12, 30, 20), "software": (12, 30, 20)}
# software threats without an honest ASVS/MASVS fit (native desktop issues); they
# must cite a CWE instead. Keep this as small as possible.
NO_CATALOG_FIT = {"library-search-path-hijack"}


@pytest.mark.parametrize("name", list(BUNDLED))
def test_bundled_library_is_complete_and_valid(name: str) -> None:
    libs = load_libraries([name])
    assert libs.issues == []
    n_el, n_th, n_me = BUNDLED[name]
    assert len(libs.elements) >= n_el
    assert len(libs.threats) >= n_th
    assert len(libs.measures) >= n_me
    method = load_method(ROOT, ProjectConfig(name="t"))
    for el in libs.elements.values():
        have = {s for t in libs.threats.values() if el.id in t.applies_to for s in t.stride}
        missing = set(method.stride_per_kind.map[el.kind]) - have
        assert not missing, f"{el.id} lacks STRIDE {sorted(missing)}"
    for t in libs.threats.values():
        assert t.measures, f"threat {t.id} suggests no measure"
        assert t.sources, f"threat {t.id} has no source"
        assert t.cra_refs, f"threat {t.id} has no CRA reference"
        if name == "iot":
            assert t.etsi303645, f"threat {t.id} has no ETSI EN 303 645 reference"
        if name == "software" and t.id in NO_CATALOG_FIT:
            assert any("CWE-" in s for s in t.sources), f"threat {t.id} cites no CWE"
        elif name == "software":
            assert t.asvs or t.masvs, f"threat {t.id} has no ASVS/MASVS reference"
    used = {m for t in libs.threats.values() for m in t.measures}
    assert set(libs.measures) <= used | {
        m.id for m in libs.measures.values() if m.kind != "technical"
    }


def test_bundled_libraries_do_not_collide() -> None:
    # A later library overrides same-kind same-ID entries of an earlier one, so
    # bundled libraries must never share an ID or combining them loses content.
    loaded = {n: load_libraries([n]) for n in BUNDLED}
    for a, b in itertools.combinations(BUNDLED, 2):
        for kind in ("elements", "threats", "measures"):
            shared = set(getattr(loaded[a], kind)) & set(getattr(loaded[b], kind))
            assert not shared, f"{a} and {b} share {kind} {sorted(shared)}"
    assert load_libraries(list(BUNDLED)).issues == []


def own_library(root: Path) -> None:
    lib = root / "libraries" / "own"
    lib.mkdir(parents=True)
    (lib / "library.yaml").write_text(
        "schema_version: 1\nid: own\nversion: '1'\nlicense: proprietary\n"
        "title:\n  de: Eigene\n  en: Own\n",
        encoding="utf-8",
    )
    (lib / "elements.yaml").write_text(
        "elements:\n  - id: plc\n    rev: 2\n    kind: device\n    name:\n      de: SPS (Hausstandard)\n"
        "      en: PLC (house standard)\n",
        encoding="utf-8",
    )


def test_project_library_overrides_and_outdated_refs(tmp_path: Path) -> None:
    root = tmp_path / "p"
    shutil.copytree(FIXTURE, root)
    own_library(root)
    project = Project.load(root)
    project.config.libraries = ["ot", "own"]
    element = project.models["main"].objects["elements"]["E-0001"]
    element.library_ref = "lib:ot/element/plc@1"
    project.models["main"].objects["elements"]["E-0002"].library_ref = "lib:ot/element/nope@1"
    project.save()

    libs = load_libraries(["ot", "own"], root)
    assert libs.elements["plc"].name.de == "SPS (Hausstandard)"
    assert libs.ref("element", "plc") == "lib:own/element/plc@2"
    issues, outdated = check_library_refs(Project.load(root), libs)
    assert [(o.object_id, o.current_rev) for o in outdated] == [("E-0001", 2)]
    assert {i.code for i in issues} == {"library-outdated", "library-ref-unknown"}
    codes = {i.code for i in validate(Project.load(root))}
    assert {"library-outdated", "library-ref-unknown"} <= codes

    out = runner.invoke(app, ["library", "update", str(root)]).stdout
    assert "main/E-0001" in out and "rev 2" in out


def test_library_cache_follows_file_changes(tmp_path: Path) -> None:
    root = tmp_path / "p"
    shutil.copytree(FIXTURE, root)
    own_library(root)
    first = load_libraries(["ot", "own"], root)
    assert load_libraries(["ot", "own"], root).elements.keys() == first.elements.keys()
    first.elements.clear()  # callers get their own containers
    assert load_libraries(["ot", "own"], root).elements

    elements = next((root / "libraries" / "own").glob("elements*.yaml"))
    text = elements.read_text(encoding="utf-8")
    elements.write_text(text.replace("SPS (Hausstandard)", "SPS (geändert)"), encoding="utf-8")
    os.utime(elements, ns=(elements.stat().st_atime_ns, elements.stat().st_mtime_ns + 10**9))
    assert load_libraries(["ot", "own"], root).elements["plc"].name.de == "SPS (geändert)"


def test_unknown_library_and_cra_ref(tmp_path: Path) -> None:
    root = tmp_path / "p"
    shutil.copytree(FIXTURE, root)
    project = Project.load(root)
    project.config.libraries = ["../evil", "missing"]
    project.models["main"].objects["threats"]["T-0001"].cra_refs = ["AI-I-2-z"]
    project.save()
    issues = validate(Project.load(root))
    assert sum(i.code == "library-invalid" for i in issues) == 2
    assert any(i.code == "unknown-cra-ref" for i in issues)


def test_new_catalog_refs_are_checked(tmp_path: Path) -> None:
    root = tmp_path / "p"
    shutil.copytree(FIXTURE, root)
    own_library(root)
    lib = root / "libraries" / "own"
    (lib / "measures.yaml").write_text(
        "measures:\n  - id: m\n    rev: 1\n    kind: technical\n"
        "    title: {de: M, en: M}\n    description: {de: M, en: M}\n",
        encoding="utf-8",
    )
    (lib / "threats.yaml").write_text(
        "threats:\n  - id: t\n    rev: 1\n    stride: [S]\n    applies_to: [plc]\n"
        "    title: {de: T, en: T}\n    scenario: {de: T, en: T}\n    consequence: {de: T, en: T}\n"
        "    etsi303645: ['5.1-1', NOPE]\n    asvs: [V0.0.0]\n    masvs: [MASVS-STORAGE-1]\n"
        "    measures: [m]\n",
        encoding="utf-8",
    )
    libs = load_libraries(["own"], root)
    assert [(i.location, i.message) for i in libs.issues] == [
        ("own/threat/t.etsi303645", "unknown reference 'NOPE'"),
        ("own/threat/t.asvs", "unknown reference 'V0.0.0'"),
    ]
    assert set(CATALOG_NAMES) == {p.stem for p in CATALOGS.glob("*.yaml")}
