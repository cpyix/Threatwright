"""Routes of data flows in diagram.layout.yaml: SVG, rename, delete, server."""

from itertools import pairwise
from pathlib import Path

from fastapi.testclient import TestClient

from threatwright.diagram import render_svg, route
from threatwright.model.delete import delete_with_refs
from threatwright.model.objects import EdgeLayout, Flow, Point
from threatwright.model.refactor import rename_id
from threatwright.model.store import Project
from threatwright.server import API_HEADER, create_app


def test_route_uses_sides_and_bend_points(project_dir: Path) -> None:
    project = Project.load(project_dir)
    sub = project.models["main"]
    flow = sub.objects["flows"]["F-0001"]
    assert isinstance(flow, Flow)
    pos = {i: (n.x, n.y) for i, n in sub.layout.nodes.items()}  # E-0001 80,120; E-0002 420,120
    assert route(sub, flow, pos) == [(250, 152), (420, 152)]  # facing sides, straight
    sub.layout.edges["F-0001"] = EdgeLayout(target_side="top", points=[Point(x=300, y=60)])
    line = route(sub, flow, pos)
    assert line[0] == (250, 152) and line[-1] == (505, 120)  # right of E-0001 -> top of E-0002
    assert all(a[0] == b[0] or a[1] == b[1] for a, b in pairwise(line))  # right angles
    assert "<polyline" in render_svg(sub)


def test_rename_and_delete_keep_routes_tidy(project_dir: Path) -> None:
    project = Project.load(project_dir)
    sub = project.models["main"]
    sub.layout.edges["F-0001"] = EdgeLayout(points=[Point(x=1, y=2)])
    rename_id(project, "main", "flows", "F-0001", "F-0042")
    assert set(sub.layout.edges) == {"F-0042"}
    delete_with_refs(sub, "elements", "E-0001", cascade=False)  # takes its flows along
    assert sub.layout.edges == {}
    project.save()
    assert "edges" not in (project_dir / "models/main/diagram.layout.yaml").read_text("utf-8")


def test_layout_endpoint_keeps_and_prunes_routes(project_dir: Path) -> None:
    client = TestClient(
        create_app(None, project_dir), base_url="http://127.0.0.1", headers={API_HEADER: "1"}
    )
    nodes = {"E-0001": {"x": 80, "y": 120}}
    edges = {"F-0001": {"source_side": "bottom", "points": [{"x": 5, "y": 6}]}, "F-9999": {}}
    client.put("/api/models/main/layout", json={"nodes": nodes, "edges": edges})
    client.put("/api/models/main/layout", json={"nodes": nodes})  # positions only: routes stay
    layout = client.get("/api/models/main").json()["layout"]
    assert (
        set(layout["edges"]) == {"F-0001"} and layout["edges"]["F-0001"]["source_side"] == "bottom"
    )
    bad = {"nodes": nodes, "edges": {"F-0001": {"source_side": "diagonal"}}}
    assert client.put("/api/models/main/layout", json=bad).status_code == 422
