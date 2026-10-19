from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from threatwright import assistant
from threatwright.diagram import render_svg
from threatwright.library import load_libraries
from threatwright.method import load_method
from threatwright.model.objects import Measure, Threat
from threatwright.model.store import Project
from threatwright.rules import validate
from threatwright.server import TOKEN_HEADER, create_app


@pytest.fixture
def loaded(project_dir: Path):  # type: ignore[no-untyped-def]
    project = Project.load(project_dir)
    project.config.libraries = ["ot"]
    return project, load_libraries(["ot"]), load_method(project_dir, project.config)


def test_add_element_and_flow_from_library(loaded) -> None:  # type: ignore[no-untyped-def]
    project, libs, _ = loaded
    sub = project.models["main"]
    before = len(sub.objects["assets"])
    plc = assistant.add_element(
        sub, libs, project.config, "plc", zone="Z-CABINET", position=(10, 20)
    )
    assert plc.kind == "device" and plc.library_ref == "lib:ot/element/plc@1"
    assert plc.title == "SPS"  # project language de
    assert len(sub.objects["assets"]) == before + len(libs.elements["plc"].assets)
    assert (sub.layout.nodes[plc.id].x, sub.layout.nodes[plc.id].y) == (10, 20)

    flow = assistant.add_flow(sub, libs, project.config, plc.id, "E-0002", "fieldbus-ethercat")
    assert flow.protocol == "EtherCAT" and flow.assets
    with pytest.raises(ValueError):
        assistant.add_element(sub, libs, project.config, "fieldbus-ethercat")
    with pytest.raises(KeyError):
        assistant.add_flow(sub, libs, project.config, plc.id, "E-9999")


def test_suggestions_adopt_and_measure_reuse(loaded) -> None:  # type: ignore[no-untyped-def]
    project, libs, method = loaded
    sub = project.models["main"]
    plc = assistant.add_element(sub, libs, project.config, "plc", zone="Z-CABINET")
    cats = assistant.suggestions(sub, libs, method, project.config, plc.id)
    assert all(cats[s].relevant and cats[s].suggestions for s in "STRIDE")

    first = cats["T"].suggestions[0]
    assert "{element}" not in first.title
    t1 = assistant.adopt_threat(sub, libs, project.config, first.template_id, plc.id)
    assert isinstance(t1, Threat) and t1.targets == [plc.id] and t1.measures
    assert t1.library_ref and t1.library_ref.startswith(f"lib:ot/threat/{first.template_id}@")
    tpl = libs.threats[first.template_id]
    assert t1.assessment.interface == (tpl.environment.interface or "local")
    assert t1.assessment.access == "restricted"  # from zone Z-CABINET

    measures_before = len(sub.objects["measures"])
    t2 = assistant.adopt_threat(sub, libs, project.config, first.template_id, plc.id)
    assert t2.measures == t1.measures  # existing measures are reused
    assert len(sub.objects["measures"]) == measures_before
    assert all(isinstance(sub.objects["measures"][m], Measure) for m in t1.measures)

    cats = assistant.suggestions(sub, libs, method, project.config, plc.id)
    adopted = [s for s in cats["T"].suggestions if s.template_id == first.template_id]
    assert adopted[0].adopted is True and t1.id in cats["T"].existing

    project.save()
    reloaded = Project.load(project.root)
    assert [i for i in validate(reloaded) if i.code == "schema"] == []
    assert reloaded.save() == []


def test_coverage_and_svg(loaded) -> None:  # type: ignore[no-untyped-def]
    project, _, method = loaded
    sub = project.models["main"]
    rows = {r.id: r for r in assistant.coverage(sub, method)}
    assert rows["E-0002"].cells["T"].existing == ["T-0001"]
    assert rows["E-0003"].kind == "external" and not rows["E-0003"].cells["T"].relevant
    assert rows["F-0001"].cells["I"].existing == ["T-0001"]

    svg = render_svg(sub, {"E-0002": 5})
    assert svg == render_svg(sub, {"E-0002": 5})  # deterministic
    assert svg.startswith("<svg") and "E-0001" in svg and "F-0001" in svg and "#f3b6b6" in svg
    sub.objects["elements"]["E-0001"].title = "<script>&"
    assert "&lt;script&gt;&amp;" in render_svg(sub)


def test_m4_endpoints(project_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("THREATWRIGHT_CONFIG_DIR", str(tmp_path / "cfg"))
    (project_dir / "threatwright.yaml").write_text(
        (project_dir / "threatwright.yaml").read_text(encoding="utf-8") + "libraries: [ot]\n",
        encoding="utf-8",
    )
    c = TestClient(
        create_app("t", None, project_dir), base_url="http://127.0.0.1", headers={TOKEN_HEADER: "t"}
    )
    assert any(e["id"] == "plc" for e in c.get("/api/library").json()["elements"])
    el = c.post("/api/models/main/add/element", json={"type": "drive", "x": 5, "y": 6}).json()
    eid = el["id"]
    flow = c.post(
        "/api/models/main/add/flow",
        json={"source": "E-0001", "target": eid, "type": "fieldbus-canopen"},
    ).json()
    assert flow["id"].startswith("F-")
    sugg = c.get(f"/api/models/main/assistant/{eid}").json()["categories"]
    tpl = sugg["T"]["suggestions"][0]["template_id"]
    adopted = c.post(f"/api/models/main/assistant/{eid}", json={"template": tpl}).json()
    assert adopted["id"] in adopted["model"]["evaluations"]
    assert adopted["model"]["max_risks"].get(eid) is None or adopted["model"]["max_risks"][eid] >= 1
    cov = c.get("/api/models/main/coverage").json()
    assert any(r["id"] == eid for r in cov)
    assert c.get("/api/models/main/diagram.svg").text.startswith("<svg")
    assert c.put("/api/models/main/layout", json={"nodes": {eid: {"x": 1, "y": 2}}}).json()["ok"]
    assert c.post("/api/models/main/add/element", json={"type": "nope"}).status_code == 422
    assert c.get("/api/models/main/assistant/E-9999").status_code == 404
