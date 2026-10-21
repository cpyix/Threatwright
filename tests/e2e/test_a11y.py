"""Automated accessibility check (axe-core, WCAG 2.1 AA) of the main views, light and dark."""

from pathlib import Path

import pytest
from conftest import ROOT, AppIdle
from playwright.sync_api import Page

AXE = ROOT / "app" / "node_modules" / "axe-core" / "axe.min.js"
VIEWS = [
    "overview",
    "setup",
    "diagram",
    "assistant",
    "coverage",
    "threats",
    "vulnerabilities",
    "validation",
    "cra",
    "changes",
    "settings",
]


@pytest.fixture
def project_dir(project_dir: Path) -> Path:
    cfg = project_dir / "threatwright.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + "libraries: [ot]\n", encoding="utf-8")
    return project_dir


@pytest.mark.skipif(not AXE.exists(), reason="axe-core not installed (npm ci in app/)")
@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_main_views_have_no_wcag_aa_violations(
    gui: str, page: Page, idle: AppIdle, offline: list[str], scheme: str
) -> None:
    page.emulate_media(color_scheme=scheme)
    page.goto(gui)
    failures: list[str] = []
    for view in VIEWS:
        page.get_by_test_id(f"nav-{view}").click()
        idle.settle()  # the view has loaded its data
        # evaluate() runs via the DevTools protocol, so the app's strict CSP stays on
        page.evaluate(AXE.read_text(encoding="utf-8"))
        result = page.evaluate(
            """() => axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']},
                                       rules: {region: {enabled: false}}})"""
        )
        for v in result["violations"]:
            if v["impact"] in ("serious", "critical"):
                targets = [n["target"][0] for n in v["nodes"][:3]]
                failures.append(f"{view}: {v['id']} ({v['impact']}) {targets}")
    assert failures == [], "\n".join(failures)
    assert offline == []
