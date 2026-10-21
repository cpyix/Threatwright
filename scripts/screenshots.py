"""Regenerate the README screenshots from a neutral demo model built from the OT library.

Run after building the GUI (cd app && npm run build):  uv run python scripts/screenshots.py
Output: docs/images/*.png. The model only uses library building blocks; no real product data.
"""

import socket
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import uvicorn
from playwright.sync_api import Page, sync_playwright

from threatwright.scaffold import create_project
from threatwright.server import API_HEADER, create_app

OUT = Path(__file__).resolve().parents[1] / "docs" / "images"

Call = Callable[..., Any]

# zone: (access, user); the interface comes from the project template
ENVIRONMENT = {
    "Z-INTERNAL": ("restricted", "non_user_related"),
    "Z-LOCAL": ("public_restricted", "instructed"),
    "Z-PLANT": ("restricted", "skilled"),
    "Z-EXTERNAL": ("non_restricted", "skilled"),
}
# key: (library type, zone, title)
ELEMENTS = {
    "plc": ("plc", "Z-INTERNAL", "Machine controller"),
    "drive": ("drive", "Z-INTERNAL", "Axis drive"),
    "io": ("remote-io", "Z-INTERNAL", "Remote I/O"),
    "hmi": ("hmi", "Z-LOCAL", "Operator panel"),
    "ews": ("engineering-workstation", "Z-PLANT", "Engineering workstation"),
    "gateway": ("remote-access-gateway", "Z-EXTERNAL", "Remote service gateway"),
}
# (source, target, flow type)
FLOWS = [
    ("hmi", "plc", "ip-network"),
    ("plc", "drive", "fieldbus-ethercat"),
    ("plc", "io", "fieldbus-ethercat"),
    ("ews", "plc", "ip-network"),
    ("gateway", "ews", "vpn-tunnel"),
]
ADOPT = {"plc": 3, "hmi": 2, "gateway": 2}  # first n suggestions per element


def build_model(call: Call) -> dict[str, str]:
    meta = call("GET", "/models/main")["meta"]
    meta["title"] = "Demo machine"
    meta["description"] = "Neutral demo model from the OT library building blocks."
    for zone in meta["zones"]:
        access, user = ENVIRONMENT[zone["id"]]
        zone["environment"] = {**zone["environment"], "access": access, "user": user}
    call("PUT", "/models/main/meta", meta)

    ids: dict[str, str] = {}
    for n, (key, (etype, zone, title)) in enumerate(ELEMENTS.items()):
        body = {"type": etype, "zone": zone, "title": title, "x": 40 + n * 220, "y": 40}
        ids[key] = call("POST", "/models/main/add/element", body)["id"]
    for source, target, ftype in FLOWS:
        body = {"source": ids[source], "target": ids[target], "type": ftype}
        call("POST", "/models/main/add/flow", body)

    for key, count in ADOPT.items():
        categories = call("GET", f"/models/main/assistant/{ids[key]}")["categories"]
        templates = [s["template_id"] for c in categories.values() for s in c["suggestions"]]
        for template in list(dict.fromkeys(templates))[:count]:  # a template may span categories
            adopted = call("POST", f"/models/main/assistant/{ids[key]}", {"template": template})
            threat = next(
                t for t in adopted["model"]["objects"]["threats"] if t["id"] == adopted["id"]
            )
            call("PUT", f"/models/main/threats/{threat['id']}", {**threat, "cyber_cause": True})

    # fields added in 0.4.0, so the compatibility sample covers them
    call(
        "PUT",
        "/project/settings",
        {"lifecycle": "development", "support_until": "2031-12-31", "next_review": "2027-06-30"},
    )
    model = call("GET", "/models/main")
    meta = {
        **model["meta"],
        "cra_not_applicable": {"AI-I-2-m": "Demo: no user data on the machine."},
    }
    call("PUT", "/models/main/meta", meta)
    measure = model["objects"]["measures"][0]
    call(
        "PUT",
        f"/models/main/measures/{measure['id']}",
        {**measure, "evidence_refs": ["https://example.invalid/test-report"]},
    )
    flow = model["objects"]["flows"][0]["id"]
    route = {"source_side": "bottom", "target_side": "top", "points": []}
    call("PUT", "/models/main/layout", {"nodes": model["layout"]["nodes"], "edges": {flow: route}})
    call("POST", "/save", {})
    return ids


def shoot(page: Page, name: str, full_page: bool = False) -> None:
    page.wait_for_timeout(600)
    page.screenshot(path=OUT / f"{name}.png", full_page=full_page)
    print(f"wrote docs/images/{name}.png")


def screenshots(page: Page, ids: dict[str, str]) -> None:
    page.get_by_test_id("nav-diagram").click()
    page.get_by_test_id("auto-layout").click()
    page.wait_for_timeout(800)
    page.keyboard.press("Control+s")  # layout saved: no unsaved marker on the save button
    page.wait_for_timeout(3000)  # toast gone
    page.locator("nav .toggle").click()  # collapsed navigation: more room for the canvas
    page.get_by_test_id("auto-layout").click()  # fit to the wider canvas
    page.get_by_test_id("legend").locator("summary").click()
    page.keyboard.press("Control+s")
    page.wait_for_timeout(3000)
    shoot(page, "diagram")
    page.locator("nav .toggle").click()

    page.get_by_test_id("nav-assistant").click()
    page.get_by_test_id("assistant-target").select_option(ids["plc"])
    shoot(page, "assistant")

    page.get_by_test_id("nav-threats").click()
    page.locator("button.rowlink").first.click()
    shoot(page, "threat")

    page.get_by_test_id("nav-coverage").click()
    shoot(page, "coverage")

    page.get_by_test_id("nav-setup").click()
    page.get_by_test_id("setup-start").click()
    page.locator("ol.steps li").nth(4).locator("button").click()  # step 5: connections
    page.locator("h2", has_text="Connections").wait_for()
    shoot(page, "setup", full_page=True)  # steps, form, list and the live diagram below


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "demo"
        create_project(root, "tr", "Demo machine", "en")  # TR template enables the OT library

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(create_app(port, root), log_level="warning"))
        threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
        while not server.started:
            time.sleep(0.05)
        base = f"http://127.0.0.1:{port}"

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": 1440, "height": 900}, locale="en-GB", color_scheme="light"
            )

            def call(method: str, path: str, body: object = None) -> Any:
                r = page.request.fetch(
                    f"{base}/api{path}", method=method, headers={API_HEADER: "1"}, data=body
                )
                assert r.ok, (method, path, r.status, r.text())
                return r.json()

            ids = build_model(call)
            page.goto(f"{base}/")
            screenshots(page, ids)
            browser.close()
        server.should_exit = True


if __name__ == "__main__":
    main()
