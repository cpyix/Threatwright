import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import FIXTURE, ROOT
from ruamel.yaml import YAML

from threatwright import __version__
from threatwright.ci import STATIC_FILES, render_ci, render_static


def _load(text: str) -> dict[str, object]:
    data = YAML(typ="safe").load(text)
    assert isinstance(data, dict)
    return data


def test_gitlab_jobs(project_dir: Path) -> None:
    text = render_ci(project_dir, "gitlab")
    data = _load(text)
    assert data["default"]["image"]["name"] == f"ghcr.io/cpyix/threatwright:{__version__}"  # type: ignore[index]
    assert data["variables"]["TW_PROJECT"] == "."  # type: ignore[index]
    validate = data["threatwright-validate"]
    assert "--strict --format junit" in " ".join(validate["script"])  # type: ignore[index]
    assert validate["artifacts"]["reports"]["junit"] == "report.xml"  # type: ignore[index]
    assert {"threatwright-build", "threatwright-diff"} <= data.keys()
    build = " ".join(data["threatwright-build"]["script"])  # type: ignore[index]
    assert "threatwright build . --template " in build
    assert "# Models: main" in text


def test_configured_template(project_dir: Path) -> None:
    cfg = project_dir / "threatwright.yaml"
    cfg.write_text(
        cfg.read_text(encoding="utf-8") + "templates:\n  - custom-doc\n", encoding="utf-8"
    )
    build = " ".join(_load(render_ci(project_dir))["threatwright-build"]["script"])  # type: ignore[index]
    assert "--template custom-doc --format docx --format md" in build


def test_github_jobs(project_dir: Path) -> None:
    data = _load(render_ci(project_dir, "github", image="registry.example/tw:1.2.3"))
    assert set(data["jobs"]) == {"validate", "build", "diff"}  # type: ignore[arg-type]
    assert data["jobs"]["validate"]["container"]["image"] == "registry.example/tw:1.2.3"  # type: ignore[index]


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_project_path_relative_to_repo() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    data = _load(render_ci(FIXTURE, "gitlab"))
    assert data["variables"]["TW_PROJECT"] == "tests/fixtures/project"  # type: ignore[index]


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_odd_path_is_quoted(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603, S607
    project = tmp_path / "docs #1 'Ü'" / "tm"
    shutil.copytree(FIXTURE, project)
    for kind in ("gitlab", "github"):
        data = _load(render_ci(project, kind))  # type: ignore[arg-type]
        env = data["variables" if kind == "gitlab" else "env"]
        assert env["TW_PROJECT"] == "docs #1 'Ü'/tm"  # type: ignore[index]


def test_rejects_unsafe_values(project_dir: Path) -> None:
    with pytest.raises(ValueError):
        render_ci(project_dir, "gitlab", image="evil\nscript: rm")
    cfg = project_dir / "threatwright.yaml"
    cfg.write_text(
        cfg.read_text(encoding="utf-8") + "templates:\n  - 'x; rm -rf /'\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        render_ci(project_dir, "gitlab")


@pytest.mark.parametrize("kind", ["gitlab", "github"])
def test_static_copies_current(kind: str) -> None:
    expected = render_static(kind)  # type: ignore[arg-type]
    _load(expected)
    actual = (ROOT / "ci" / STATIC_FILES[kind]).read_text(encoding="utf-8")  # type: ignore[index]
    assert actual == expected, "regenerate with: uv run python -m threatwright.ci"
