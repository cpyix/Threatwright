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
@pytest.mark.parametrize("kind", ["ot", "iot", "software"])
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
