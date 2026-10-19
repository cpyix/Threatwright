import shutil
from pathlib import Path

from conftest import FIXTURE, ROOT
from typer.testing import CliRunner

from threatwright.cli import app
from threatwright.library import check_library_refs, load_libraries
from threatwright.method import load_method
from threatwright.model.objects import ProjectConfig
from threatwright.model.store import Project
from threatwright.rules import validate

runner = CliRunner()


def test_bundled_ot_library_is_complete_and_valid() -> None:
    libs = load_libraries(["ot"])
    assert libs.issues == []
    assert len(libs.elements) >= 25
    assert len(libs.threats) >= 120
    assert len(libs.measures) >= 80
    method = load_method(ROOT, ProjectConfig(name="t"))
    for el in libs.elements.values():
        have = {s for t in libs.threats.values() if el.id in t.applies_to for s in t.stride}
        missing = set(method.stride_per_kind.map[el.kind]) - have
        assert not missing, f"{el.id} lacks STRIDE {sorted(missing)}"
    for t in libs.threats.values():
        assert t.measures, f"threat {t.id} suggests no measure"
        assert t.sources, f"threat {t.id} has no source"
    used = {m for t in libs.threats.values() for m in t.measures}
    assert set(libs.measures) <= used | {
        m.id for m in libs.measures.values() if m.kind != "technical"
    }


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
