"""Deleting an element in the diagram asks whether its threats and measures go too."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.parametrize(("button", "kept"), [("delete-cascade", False), ("delete-keep", True)])
def test_delete_element_asks_about_related(gui: str, page: Page, button: str, kept: bool) -> None:
    page.goto(gui)
    page.get_by_test_id("nav-diagram").click()
    page.get_by_test_id("node-E-0002").click()
    page.get_by_test_id("object-form").get_by_test_id("delete").click()

    dialog = page.get_by_test_id("delete-dialog")
    # its flow, the threat on both, that threat's measure
    for oid in ("F-0001", "T-0001", "M-0001"):
        expect(dialog).to_contain_text(oid)
    dialog.get_by_test_id(button).click()
    expect(page.get_by_test_id("node-E-0002")).to_be_hidden()

    model = page.request.get(f"{gui}api/models/main", headers={"X-Threatwright": "1"}).json()
    ids = {c: {o["id"] for o in model["objects"][c]} for c in ("flows", "threats", "measures")}
    assert "F-0001" not in ids["flows"]
    assert ("T-0001" in ids["threats"], "M-0001" in ids["measures"]) == (kept, kept)
