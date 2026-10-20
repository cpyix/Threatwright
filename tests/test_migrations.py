"""The migration chain itself (ADR-0015), exercised with a pretend schema version 2."""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from threatwright.cli import app
from threatwright.model import migrations, objects, store
from threatwright.model.migrations import NewerSchemaError, upgrade
from threatwright.model.store import Project


def test_current_documents_are_left_alone() -> None:
    doc = {"schema_version": objects.SCHEMA_VERSION, "title": "x"}
    assert upgrade("Element", doc) is False and doc["title"] == "x"


def test_steps_run_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(objects, "SCHEMA_VERSION", 3)
    seen: list[str] = []
    monkeypatch.setitem(migrations.MIGRATIONS, 1, lambda kind, d: seen.append(f"1:{kind}"))
    monkeypatch.setitem(
        migrations.MIGRATIONS, 2, lambda kind, d: d.update(name=d.pop("title")) or seen.append("2")
    )
    doc = {"schema_version": 1, "title": "Controller"}
    assert upgrade("Element", doc) is True
    assert seen == ["1:Element", "2"]
    assert doc == {"schema_version": 3, "name": "Controller"}


def test_newer_and_invalid_versions_are_refused() -> None:
    with pytest.raises(NewerSchemaError, match="newer Threatwright"):
        upgrade("Element", {"schema_version": objects.SCHEMA_VERSION + 1})
    for bad in (0, "1", True):
        with pytest.raises(ValueError, match="invalid schema_version"):
            upgrade("Element", {"schema_version": bad})


def test_file_from_newer_release_gives_a_clear_issue(project_dir: Path) -> None:
    element = project_dir / "models" / "main" / "elements" / "E-0001.yaml"
    element.write_text(
        element.read_text("utf-8").replace("schema_version: 1", "schema_version: 99"), "utf-8"
    )
    issues = Project.load(project_dir).issues
    assert len(issues) == 1 and "newer Threatwright" in issues[0].message


def test_migrate_command(
    project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    assert "nothing to migrate" in runner.invoke(app, ["migrate", str(project_dir)]).output

    # every file reports "was older": migrate must write each of them, once
    copy = tmp_path / "old"
    shutil.copytree(project_dir, copy)
    monkeypatch.setattr(store, "upgrade", lambda kind, doc: True)
    result = runner.invoke(app, ["migrate", str(copy)])
    files = len(list(copy.rglob("*.yaml")))  # the fixture holds project files only
    assert f"migrated {files} file(s)" in result.output, result.output
    monkeypatch.undo()
    assert "nothing to migrate" in runner.invoke(app, ["migrate", str(copy)]).output
