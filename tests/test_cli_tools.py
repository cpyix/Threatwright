import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import ROOT
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from threatwright.cli import app
from threatwright.server import TOKEN_HEADER, create_app

runner = CliRunner()
DRAGON = ROOT / "tests" / "fixtures" / "interop" / "threat-dragon-v2.json"


def test_export_and_import(project_dir: Path) -> None:
    r = runner.invoke(app, ["export", str(project_dir), "--format", "xlsx"])
    assert r.exit_code == 0, r.output
    assert (project_dir / "build" / "threats.xlsx").exists()
    r = runner.invoke(
        app,
        [
            "import",
            str(DRAGON),
            "--from",
            "threat-dragon",
            "--model",
            "dragon",
            "--path",
            str(project_dir),
        ],
    )
    assert r.exit_code == 0, r.output
    assert "imported into model 'dragon'" in r.output
    # imported threats without a mitigation are real findings, not schema errors
    out = runner.invoke(app, ["validate", str(project_dir), "--format", "json"]).stdout
    assert "(schema)" not in out and '"schema"' not in out
    assert "threat-without-measure" in out


def git(cwd: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        [  # noqa: S607 - git from PATH is intended in tests
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "tag.gpgsign=false",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_diff_and_change_markers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "tests" / "fixtures" / "project", repo / "product")
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "v1")
    git(repo, "tag", "v1")
    threat = repo / "product/models/main/threats/T-0001.yaml"
    threat.write_text(
        threat.read_text(encoding="utf-8").replace("impact: 4", "impact: 5"), encoding="utf-8"
    )

    r = runner.invoke(app, ["diff", "v1", "--path", str(repo / "product")])
    assert r.exit_code == 0, r.output
    assert "T-0001" in r.output

    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "cfg"))
    c = TestClient(
        create_app("t", None, repo / "product"),
        base_url="http://127.0.0.1",
        headers={TOKEN_HEADER: "t"},
    )
    data = c.get("/api/vcs/changed").json()
    assert data["available"] and data["models"]["main"] == ["T-0001"]
    assert [t["name"] for t in data["tags"]] == ["v1"]


def test_change_markers_without_git(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    c = TestClient(
        create_app("t", None, project_dir), base_url="http://127.0.0.1", headers={TOKEN_HEADER: "t"}
    )
    assert c.get("/api/vcs/changed").json()["available"] is False
