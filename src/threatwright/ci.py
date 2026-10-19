"""CI pipeline templates (ADR-0009): one Jinja source for GUI, CLI and the copies in ci/."""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from threatwright import __version__
from threatwright.model.store import LoadError, Project
from threatwright.render.package import TemplateError
from threatwright.render.package import active as active_templates

CiKind = Literal["gitlab", "github"]

# Owner of the published image. Stays a placeholder until the release namespace is fixed;
# users replace OWNER or pass --image.
IMAGE_REPO = "ghcr.io/OWNER/threatwright"
DEFAULT_FORMATS = ["docx", "md"]
DEFAULT_DOCUMENTS = {"tr-analysis": DEFAULT_FORMATS}

TEMPLATE_FILES: dict[CiKind, str] = {
    "gitlab": "gitlab-ci.yml.j2",
    "github": "github-actions.yml.j2",
}
TARGET_FILES: dict[CiKind, str] = {
    "gitlab": ".gitlab-ci.yml",
    "github": ".github/workflows/threatwright.yml",
}
STATIC_FILES: dict[CiKind, str] = {"gitlab": "gitlab-ci.yml", "github": "github-actions.yml"}

# Values that end up in YAML/shell unquoted must be plain tokens.
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9./:@_-]*$")

_env = SandboxedEnvironment(
    loader=FileSystemLoader(Path(__file__).parent / "ci_templates"),
    # GitHub expressions use ${{ }}; distinct delimiters keep both templates readable.
    block_start_string="[%",
    block_end_string="%]",
    variable_start_string="[[",
    variable_end_string="]]",
    comment_start_string="[#",
    comment_end_string="#]",
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
    autoescape=False,  # noqa: S701 - output is YAML, not HTML
)
# JSON strings are valid YAML double-quoted scalars.
_env.filters["yaml_str"] = lambda s: json.dumps(str(s), ensure_ascii=False)


def repo_root(project_root: Path) -> Path | None:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        out = subprocess.run(  # noqa: S603 - fixed argv, local git only
            [git, "-C", str(project_root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            encoding="utf-8",
            check=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(out) if out else None


def _project_path(project_root: Path) -> str:
    root = repo_root(project_root)
    if root is None:
        return "."
    try:
        rel = project_root.resolve().relative_to(root.resolve())
    except ValueError:
        return "."
    return rel.as_posix() or "."


def _tokens(values: list[str], what: str) -> list[str]:
    for v in values:
        if not _TOKEN.match(v):
            raise ValueError(
                f"{what} '{v}' cannot be used in a pipeline (allowed: A-Z a-z 0-9 . _ -)"
            )
    return values


def ci_context(
    project_root: Path | None, image: str | None = None, version: str | None = None
) -> dict[str, object]:
    """Template values; project_root None gives the generic values of the ci/ copies."""
    image = image or f"{IMAGE_REPO}:{version or __version__}"
    if not _IMAGE.match(image):
        raise ValueError(f"invalid image reference: {image}")
    models: list[str] = []
    documents = DEFAULT_DOCUMENTS
    path = "."
    if project_root is not None:
        project_root = Path(project_root)
        path = _project_path(project_root)
        try:
            project = Project.load(project_root)
        except LoadError:
            project = None
        if project is not None:
            models = _tokens(sorted(project.models), "model")
            documents = _documents(project)
    return {
        "image": image,
        "project_path": path,
        "models": models,
        "documents": documents,
    }


def _documents(project: Project) -> dict[str, list[str]]:
    """Active document templates and the formats each one offers."""
    docs: dict[str, list[str]]
    try:
        docs = {p.meta.id: sorted(p.meta.all_files) for p in active_templates(project)}
    except TemplateError:
        # Broken or missing template: still offer a pipeline, the build job will report it.
        docs = {t: DEFAULT_FORMATS for t in project.config.templates}
    for t, formats in docs.items():
        _tokens([t, *formats], "template")
    return docs or DEFAULT_DOCUMENTS


def render_ci(
    project_root: Path | None,
    kind: CiKind = "gitlab",
    image: str | None = None,
    version: str | None = None,
) -> str:
    return _env.get_template(TEMPLATE_FILES[kind]).render(ci_context(project_root, image, version))


def target_path(project_root: Path, kind: CiKind = "gitlab") -> Path:
    """Where the pipeline file belongs (for the explicit "write" action in the GUI)."""
    return (repo_root(project_root) or Path(project_root)) / TARGET_FILES[kind]


def render_static(kind: CiKind) -> str:
    """Content of the generic copies in ci/ (image tag left as a placeholder)."""
    return render_ci(None, kind, image=f"{IMAGE_REPO}:VERSION")


if __name__ == "__main__":
    # Regenerate ci/ from the repository root: uv run python -m threatwright.ci
    for k, name in STATIC_FILES.items():
        Path("ci", name).write_text(render_static(k), encoding="utf-8", newline="\n")
