"""GUI: change evidence against a release tag, from the state in the editor."""

import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import AppIdle
from playwright.sync_api import Page, expect

GIT = shutil.which("git")


def git(repo: Path, *args: str) -> None:
    cfg = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
    cfg += ["-c", "tag.gpgsign=false", "-c", "core.autocrlf=false"]
    subprocess.run([GIT or "git", *cfg, *args], cwd=repo, check=True, capture_output=True)  # noqa: S603


@pytest.mark.skipif(GIT is None, reason="git not installed")
def test_changes_since_tag(
    gui: str, page: Page, idle: AppIdle, offline: list[str], project_dir: Path
) -> None:
    git(project_dir, "init", "-q", "-b", "main")
    git(project_dir, "add", "-A")
    git(project_dir, "commit", "-q", "-m", "v1")
    git(project_dir, "tag", "v1.0")
    page.goto(gui)
    page.get_by_test_id("nav-measures").click()
    page.get_by_role("button", name="M-0001", exact=True).click()
    form = page.get_by_test_id("object-form")
    form.get_by_test_id("field-status").select_option("implemented")
    form.get_by_test_id("apply").click()
    idle.settle()
    page.get_by_test_id("nav-changes").click()
    idle.settle()
    expect(page.get_by_test_id("diff-since")).to_have_value("v1.0")
    expect(page.get_by_test_id("diff-M-0001")).to_contain_text("implemented")
    assert offline == [], f"unexpected outbound requests: {offline}"
