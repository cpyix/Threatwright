"""GUI: attach a link and a file as evidence to a measure."""

from pathlib import Path

from conftest import AppIdle
from playwright.sync_api import Page, expect


def test_attach_evidence(
    gui: str, page: Page, idle: AppIdle, offline: list[str], tmp_path: Path, project_dir: Path
) -> None:
    report = tmp_path / "pentest.pdf"
    report.write_bytes(b"%PDF-1.7")
    page.goto(gui)
    page.get_by_test_id("nav-measures").click()
    page.get_by_role("button", name="M-0001", exact=True).click()
    form = page.get_by_test_id("object-form")
    form.get_by_test_id("evidence-link").fill("https://wiki.example/report")
    form.get_by_test_id("evidence-link").press("Enter")
    form.get_by_test_id("evidence-file").set_input_files(report)
    expect(form.get_by_test_id("evidence-refs")).to_contain_text("evidence/pentest.pdf")
    form.get_by_test_id("apply").click()
    idle.save()  # after the measure update arrived, never before
    text = (project_dir / "models/main/measures/M-0001.yaml").read_text(encoding="utf-8")
    assert "https://wiki.example/report" in text and "evidence/pentest.pdf" in text
    assert (project_dir / "evidence" / "pentest.pdf").read_bytes() == b"%PDF-1.7"
    assert offline == [], f"unexpected outbound requests: {offline}"
