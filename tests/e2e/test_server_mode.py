"""Server mode in the GUI: open projects on the server, upload a local one, download it again."""

from pathlib import Path

from playwright.sync_api import Page, expect

from threatwright import archive


def test_server_projects_upload_download(
    server_gui: str, page: Page, workspace: Path, project_dir: Path, tmp_path: Path
) -> None:
    page.goto(server_gui)
    projects = page.get_by_test_id("server-projects")
    expect(projects).to_contain_text("machine-a")
    expect(page.get_by_test_id("browse-new")).to_have_count(0)  # no dialog on the server

    local_zip = tmp_path / "laptop-project.zip"
    local_zip.write_bytes(archive.pack(project_dir))
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
