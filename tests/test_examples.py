"""Example projects per product type: valid, canonical and renderable."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from threatwright.cli import app
from threatwright.model.store import Project
from threatwright.render import build_documents
from threatwright.rules import validate
from threatwright.scaffold import create_project


@pytest.mark.parametrize("lang", ["de", "en"])
@pytest.mark.parametrize("kind", ["ot", "iot", "software", "embedded-linux"])
def test_example_is_valid_and_complete(tmp_path: Path, kind: str, lang: str) -> None:
    root = tmp_path / kind
    create_project(root, "tr", None, lang, [kind], example=True)  # type: ignore[arg-type]
    project = Project.load(root)
    assert [i for i in validate(project) if i.severity == "error"] == []
    sub = project.models["main"]
    statuses = {t.status for t in sub.objects["threats"].values()}  # type: ignore[attr-defined]
    assert {"assessed", "accepted"} <= statuses
    assert any(m.status == "implemented" for m in sub.objects["measures"].values())  # type: ignore[attr-defined]
    assert len(sub.layout.nodes) == len(sub.objects["elements"])
    assert project.save() == []  # canonical right after creation
    assert build_documents(root, "main", "tr-analysis", "md")


def test_cli_and_empty_template(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["init", str(tmp_path / "x"), "-l", "iot", "--example"])
    assert result.exit_code == 0, result.output
    assert Project.load(tmp_path / "x").models["main"].objects["threats"]
    with pytest.raises(ValueError, match="template 'tr'"):
        create_project(tmp_path / "y", "empty", example=True)


@pytest.mark.parametrize("lang", ["de", "en"])
def test_embedded_linux_example_has_a_refining_sub_model(tmp_path: Path, lang: str) -> None:
    root = tmp_path / "el"
    r = CliRunner().invoke(
        app, ["init", str(root), "-l", "embedded-linux", "--example", "--language", lang]
    )
    assert r.exit_code == 0, r.output
    project = Project.load(root)
    assert project.config.libraries == ["ot", "embedded-linux"]
    assert set(project.models) == {"main", "software"}
    sw = project.models["software"]
    host = next(e for e in sw.objects["elements"].values() if getattr(e, "refines", None))
    assert host.refines.startswith("main/")  # type: ignore[attr-defined]
    hosted = [e for e in sw.objects["elements"].values() if getattr(e, "runs_on", None) == host.id]
    assert {e.privilege.level for e in hosted if e.privilege} >= {"root", "user"}  # type: ignore[attr-defined]
    assert sw.objects["threats"]
    assert CliRunner().invoke(app, ["validate", str(root)]).exit_code == 0  # 0 errors
    written = build_documents(root, None, None, "md")
    assert written and not any(p.name.startswith("software-") for p in written)  # one assessment
    text = (root / "build" / "main-tr-analysis.md").read_text("utf-8")
    assert "software/E-0002" in text
