"""Processes on a host: frames for host and privilege contexts, boundary style, form fields,
and the library filter of the palette."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import AppIdle, _serve, _set_language
from playwright.sync_api import Page, expect

from threatwright.model.objects import Element, Flow
from threatwright.model.store import Project


@pytest.fixture
def hosted_gui(
    project_dir: Path, ui_lang: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[str]:
    """Fixture project plus two processes with different rights on the controller E-0001."""
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "config"))
    _set_language(project_dir, ui_lang)
    project = Project.load(project_dir)
    project.config.libraries = ["ot", "software"]
    sub = project.models["main"]
    for eid, title, level in (("E-0010", "Runtime", "root"), ("E-0011", "Operator UI", "user")):
        sub.objects["elements"][eid] = Element.model_validate(
            {
                "id": eid,
                "title": title,
                "kind": "process",
                "runs_on": "E-0001",
                "privilege": {"level": level},
            }
        )
    sub.objects["flows"]["F-0010"] = Flow(
        id="F-0010", title="Commands", source="E-0011", target="E-0010"
    )
    project.save()
    yield from _serve(project_dir)


def test_host_frames_and_privilege_boundary(hosted_gui: str, page: Page, idle: AppIdle) -> None:
    page.goto(hosted_gui)
    page.get_by_test_id("nav-diagram").click()
    expect(page.get_by_test_id("host-E-0001")).to_be_visible()
    expect(page.locator("[data-testid^='context-']")).to_have_count(2)  # root and user
    expect(page.locator(".svelte-flow__edge.cross-privilege")).to_have_count(1)
    # the processes inherit the zone of their host: no zone crossing between them
    expect(page.locator(".svelte-flow__edge.cross-zone")).to_have_count(1)  # only F-0001

    idle.settle()
    page.get_by_test_id("auto-layout").click()  # hosts nest inside zones in ELK
    idle.settle()
    expect(page.get_by_test_id("host-E-0001")).to_be_visible()


def test_process_form_shows_host_fields(
    hosted_gui: str, page: Page, idle: AppIdle, project_dir: Path
) -> None:
    page.goto(hosted_gui)
    page.get_by_test_id("nav-diagram").click()
    page.get_by_test_id("node-E-0010").click()
    form = page.get_by_test_id("object-form")
    expect(form.get_by_test_id("field-runs_on")).to_have_value("E-0001")
    expect(form.get_by_test_id("field-runs_on").locator("option[value='E-0010']")).to_have_count(0)
    form.get_by_test_id("field-authentication").select_option("none")
    form.get_by_test_id("listener-add").click()
    form.get_by_test_id("listeners").locator("input").first.fill("5000")
    form.get_by_test_id("listeners").locator("input").first.press("Tab")
    form.get_by_test_id("apply").click()
    idle.settle()
    idle.save()
    el = Project.load(project_dir).models["main"].objects["elements"]["E-0010"]
    assert isinstance(el, Element)
    assert el.authentication == "none" and el.listens_on[0].port == 5000

    page.get_by_test_id("node-E-0003").click()  # external entity: no host fields
    expect(page.get_by_test_id("object-form").get_by_test_id("field-runs_on")).to_have_count(0)


def test_palette_filters_by_library(hosted_gui: str, page: Page) -> None:
    page.goto(hosted_gui)
    page.get_by_test_id("nav-diagram").click()
    expect(page.get_by_test_id("palette-plc")).to_be_visible()
    expect(page.get_by_test_id("palette-desktop-app")).to_be_visible()
    page.get_by_test_id("palette-library-software").check()
    expect(page.get_by_test_id("palette-plc")).to_have_count(0)
    expect(page.get_by_test_id("palette-desktop-app")).to_be_visible()
    page.reload()  # remembered in the browser
    page.get_by_test_id("nav-diagram").click()
    expect(page.get_by_test_id("palette-library-software")).to_be_checked()
    expect(page.get_by_test_id("palette-plc")).to_have_count(0)
    page.get_by_test_id("palette-library-software").uncheck()
    expect(page.get_by_test_id("palette-plc")).to_be_visible()
