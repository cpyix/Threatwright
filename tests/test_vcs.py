import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import FIXTURE

from threatwright.method import load_method
from threatwright.model.objects import Decision, Measure
from threatwright.model.store import Project
from threatwright.vcs import (
    VcsError,
    changed_objects,
    load_project_at,
    release_tags,
    render_diff,
    semantic_diff,
)

GIT = shutil.which("git")
pytestmark = pytest.mark.skipif(GIT is None, reason="git not installed")


def git(repo: Path, *args: str) -> str:
    cfg = [
        "-c", "user.name=t", "-c", "user.email=t@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false",
        "-c", "core.autocrlf=false",
    ]  # fmt: skip
    out = subprocess.run(  # noqa: S603
        [GIT or "git", *cfg, *args], cwd=repo, capture_output=True, check=True, timeout=60
    )
    return out.stdout.decode()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repo with the fixture project in a subfolder with spaces and umlauts."""
    root = tmp_path / "Repo mit Ümlaut"
    shutil.copytree(FIXTURE, root / "Ordner ä" / "project")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "v1")
    git(root, "tag", "-a", "v1.0", "-m", "release")
    return root / "Ordner ä" / "project"


def edit_and_commit(project_dir: Path) -> None:
    project = Project.load(project_dir)
    main = project.models["main"]
    threat = main.objects["threats"]["T-0001"]
    threat.status = "rejected"
    threat.rejection = Decision(rationale="Not reachable.")
    threat.assessment.impact = 2
    main.objects["measures"]["M-0002"] = Measure(id="M-0002", title="New measure")
    del main.objects["questions"]["Q-0001"]
    project.save()
    git(project_dir, "add", "-A")
    git(project_dir, "commit", "-q", "-m", "v2")


def test_load_project_at_revision(repo: Path) -> None:
    edit_and_commit(repo)
    old = load_project_at(repo, "v1.0")
    assert old.issues == []
    assert old.models["main"].objects["threats"]["T-0001"].status == "assessed"  # type: ignore[attr-defined]
    assert "Q-0001" in old.models["main"].objects["questions"]
    current = load_project_at(repo, None)
    assert "Q-0001" not in current.models["main"].objects["questions"]


def test_semantic_diff_and_render(repo: Path) -> None:
    edit_and_commit(repo)
    old, new = load_project_at(repo, "v1.0"), load_project_at(repo, "HEAD")
    method = load_method(repo, new.config)
    diff = semantic_diff(old, new, method, "v1.0", "HEAD")
    objs = {(o.collection, o.id): o for o in diff.models[0].objects}
    t = objs[("threats", "T-0001")]
    assert t.change == "changed"
    assert set(t.fields) == {"assessment", "status", "rejection"}
    assert t.status == ("assessed", "rejected")
    assert t.risk is not None and t.risk[0] is not None and t.risk[1] is not None
    assert t.risk[1] < t.risk[0]
    assert objs[("measures", "M-0002")].change == "added"
    assert objs[("questions", "Q-0001")].change == "removed"
    assert ("elements", "E-0001") not in objs

    md = render_diff(diff)
    assert "# Änderungsnachweis" in md
    assert "neu abgelehnt" in md
    assert "**M-0002** New measure: neu" in md
    assert render_diff(diff) == md  # deterministic
    assert "Change evidence" in render_diff(diff, lang="en")
    data = json.loads(render_diff(diff, "json"))
    assert data["models"][0]["name"] == "main"


def test_diff_matches_by_uuid_when_id_changes(project_dir: Path) -> None:
    old = Project.load(project_dir)
    new = Project.load(project_dir)
    measures = new.models["main"].objects["measures"]
    m = measures.pop("M-0001")
    m.id = "M-0009"
    measures["M-0009"] = m
    diff = semantic_diff(old, new, load_method(project_dir, new.config))
    (change,) = [o for o in diff.models[0].objects if o.collection == "measures"]
    assert (change.change, change.id, change.old_id, change.fields) == (
        "changed",
        "M-0009",
        "M-0001",
        ["id"],
    )


def test_no_changes(project_dir: Path) -> None:
    p = Project.load(project_dir)
    diff = semantic_diff(p, Project.load(project_dir), load_method(project_dir, p.config))
    assert diff.empty
    assert "Keine inhaltlichen Änderungen." in render_diff(diff)


def test_changed_objects_and_tags(repo: Path) -> None:
    assert changed_objects(repo) == {}
    edit_and_commit(repo)
    assert changed_objects(repo) == {}
    assert changed_objects(repo, "v1.0") == {"main": {"T-0001", "M-0002", "Q-0001"}}
    (repo / "models" / "main" / "elements" / "E-0003.yaml").write_text(
        "schema_version: 1\nid: E-0003\ntitle: Changed\nkind: external\n", encoding="utf-8"
    )
    new_file = repo / "models" / "main" / "assets" / "A-0003.yaml"
    new_file.write_text("x: 1\n", encoding="utf-8")  # untracked
    assert changed_objects(repo) == {"main": {"E-0003", "A-0003"}}
    assert [t.name for t in release_tags(repo)] == ["v1.0"]


def test_errors(tmp_path: Path, repo: Path) -> None:
    with pytest.raises(VcsError, match="not inside a Git repository"):
        changed_objects(tmp_path)
    with pytest.raises(VcsError, match="invalid revision"):
        load_project_at(repo, "--output=x")
    with pytest.raises(VcsError):
        load_project_at(repo, "does-not-exist")


def test_git_missing(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(VcsError, match="not installed"):
        release_tags(repo)
