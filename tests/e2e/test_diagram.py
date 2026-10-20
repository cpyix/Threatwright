"""M4 end-to-end: build a model from library blocks, adopt suggestions, check coverage."""

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from threatwright.model.store import Project


@pytest.fixture
def project_dir(project_dir: Path) -> Path:
    cfg = project_dir / "threatwright.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + "libraries: [ot]\n", encoding="utf-8")
    return project_dir


def test_diagram_assistant_coverage(
    ui: dict[str, str], gui: str, page: Page, offline: list[str], project_dir: Path
) -> None:
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(gui)
    page.get_by_test_id("nav-diagram").click()

    page.drag_and_drop(
        "[data-testid=palette-drive]", ".svelte-flow__pane", target_position={"x": 500, "y": 420}
    )
    expect(page.get_by_test_id("node-E-0004")).to_be_visible()

    page.get_by_test_id("flow-type").select_option("fieldbus-ethercat")
    source = page.locator("[data-testid=node-E-0001] .svelte-flow__handle-bottom")
    target = page.locator("[data-testid=node-E-0004] .svelte-flow__handle-top")
    source.hover()
    page.mouse.down()
    target.hover()
    target.hover()
    page.mouse.up()
    expect(page.locator(".svelte-flow__edge")).to_have_count(2)

    page.get_by_test_id("node-E-0004").click()
    page.get_by_test_id("open-assistant").click()
    expect(page.get_by_test_id("assistant-target")).to_have_value("E-0004")
    page.locator("[data-testid^=adopt-]").first.click()
    expect(page.get_by_test_id("cyber-dialog")).to_be_hidden()  # rule 3.3 answered by the template
    expect(page.locator("span.ok").first).to_be_visible()  # adopted

    page.get_by_test_id("nav-coverage").click()
    expect(page.get_by_test_id("coverage")).to_contain_text("E-0004")

    page.keyboard.press("Control+s")
    # Save can exceed the 5 s default on slow Windows CI runners
    expect(page.get_by_test_id("toast")).to_contain_text(ui["saved"], timeout=15_000)
    project = Project.load(project_dir)
    sub = project.models["main"]
    assert sub.objects["elements"]["E-0004"].library_ref == "lib:ot/element/drive@1"
    assert any(
        f.library_ref == "lib:ot/element/fieldbus-ethercat@1" for f in sub.objects["flows"].values()
    )
    adopted = [
        t for t in sub.objects["threats"].values() if t.library_ref and "E-0004" in t.targets
    ]
    assert adopted and adopted[0].cyber_cause is True and adopted[0].measures
    assert "E-0004" in sub.layout.nodes
    assert offline == [] and errors == []
