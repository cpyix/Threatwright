"""Server mode in the GUI: open projects on the server, upload a local one, download it again."""

import re
from pathlib import Path

from playwright.sync_api import Page, expect

from threatwright import archive


def test_server_projects_upload_download(
    server_gui: str, page: Page, workspace: Path, project_dir: Path, tmp_path: Path
) -> None:
    page.goto(server_gui)
    projects = page.get_by_test_id("server-projects")
    expect(projects).to_contain_text("machine-a")  # overview first, cards with name and folder
    expect(projects).to_contain_text("Test fixture project")
    expect(page.get_by_test_id("new-path")).to_have_count(0)  # forms only on demand
    page.get_by_test_id("show-new-project").click()
    expect(page.get_by_test_id("new-path")).to_be_visible()
    expect(page.get_by_test_id("browse-new")).to_have_count(0)  # no dialog on the server

    local_zip = tmp_path / "laptop-project.zip"
    local_zip.write_bytes(archive.pack(project_dir))
    page.get_by_test_id("show-upload").click()
    page.get_by_test_id("zip-file").set_input_files(local_zip)
    page.get_by_test_id("upload-project").click()
    expect(page.get_by_test_id("nav-diagram")).to_have_attribute("aria-current", "page")
    assert (workspace / "laptop-project" / "threatwright.yaml").is_file()

    page.get_by_test_id("nav-start").click()
    expect(projects).to_contain_text("laptop-project")
    with page.expect_download() as dl:
        page.get_by_test_id("download-project").click()
    assert dl.value.suggested_filename.endswith(".zip")

    page.get_by_test_id("open-server-machine-a").click()
    expect(page.get_by_test_id("nav-diagram")).to_have_attribute("aria-current", "page")

    page.reload()  # a later visit starts on the overview, the open project is marked
    expect(page.get_by_test_id("open-server-machine-a")).to_have_class(re.compile(r"\bcurrent\b"))


def test_server_oscal_import_with_file_picker(server_gui: str, page: Page) -> None:
    """The catalog file comes from the browser's machine; no server path to type in."""
    catalog = Path(__file__).parents[1] / "fixtures" / "oscal" / "synthetic-arc-catalog.json"
    page.goto(server_gui)
    page.get_by_test_id("open-server-machine-a").click()
    expect(page.get_by_test_id("nav-diagram")).to_have_attribute("aria-current", "page")
    page.get_by_test_id("nav-settings").click()
    page.get_by_test_id("oscal-file").set_input_files(catalog)
    page.get_by_test_id("oscal-import").click()
    expect(page.locator("pre.note")).to_contain_text("libraries/")
    expect(page.locator("table")).to_contain_text("synthetic")
