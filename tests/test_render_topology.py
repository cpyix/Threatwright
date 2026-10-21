"""Documents and diagram show runs_on, privilege contexts, refines and the attack surface."""

from pathlib import Path

from threatwright.diagram import render_svg
from threatwright.model.objects import Assessment, Element, Flow, ModelMeta, Threat
from threatwright.model.store import Project, SubModel
from threatwright.render import build_documents
from threatwright.scaffold import create_project


def _product(root: Path) -> Project:
    create_project(root, language="de")
    project = Project.load(root)
    main = project.models["main"]
    main.objects["elements"]["E-0001"] = Element(
        id="E-0001", title="Steuerungsrechner", kind="device", zone="Z-PLANT"
    )
    main.objects["threats"]["T-0001"] = Threat(
        id="T-0001", title="Gehäuse wird geöffnet", targets=["E-0001"], stride=["T"]
    )
    sw = SubModel("software", ModelMeta(title="Steuerungssoftware"))
    els = {
        "E-0001": Element(id="E-0001", title="IPC", kind="device", refines="main/E-0001"),
        "E-0002": Element.model_validate(
            {
                "id": "E-0002",
                "title": "Echtzeitprozess",
                "kind": "process",
                "runs_on": "E-0001",
                "privilege": {"level": "root"},
                "listens_on": [{"protocol": "tcp", "port": 5000}],
                "authentication": "none",
                "memory_safe": False,
                "sbom_ref": {"purl": "pkg:generic/rt-control@1.0"},
            }
        ),
        "E-0003": Element.model_validate(
            {
                "id": "E-0003",
                "title": "Bedienoberfläche",
                "kind": "process",
                "runs_on": "E-0001",
                "privilege": {"level": "user", "account": "operator"},
            }
        ),
    }
    sw.objects["elements"] = dict(els)
    sw.objects["flows"]["F-0001"] = Flow(
        id="F-0001", title="Befehle", source="E-0003", target="E-0002"
    )
    sw.objects["threats"]["T-0001"] = Threat(
        id="T-0001",
        title="Bedienoberfläche sendet fremde Befehle",
        targets=["F-0001"],
        stride=["E"],
        assessment=Assessment(interface="local", access="restricted", user="instructed", impact=4),
    )
    project.models["software"] = sw
    project.save()
    return project


def test_one_document_per_product_with_sub_model(tmp_path: Path) -> None:
    root = tmp_path / "p"
    _product(root)
    written = build_documents(root, None, "tr-analysis", "md")
    assert [p.name for p in written] == ["main-tr-analysis.md"]  # no second assessment
    text = written[0].read_text("utf-8")
    assert "Teilmodell: Steuerungssoftware (verfeinert main/E-0001)" in text
    assert "software/T-0001" in text and "software/E-0002" in text  # qualified ids
    assert "verfeinert in software/E-0001" in text  # main element links its refinement
    assert "Läuft auf" in text and "software/E-0001 IPC" in text
    assert "root" in text and "Benutzerkonto (operator)" in text
    assert "| Grenze |" in text and "Rechtekontext" in text
    assert "Technische Angriffsfläche" in text and "tcp/5000 (all)" in text
    assert "pkg:generic/rt-control@1.0" in text
    # the sub-model can still be built on its own
    alone = build_documents(root, "software", "tr-analysis", "md", tmp_path / "out")
    assert [p.name for p in alone] == ["software-tr-analysis.md"]


def test_old_model_document_has_no_new_columns(tmp_path: Path) -> None:
    root = tmp_path / "p"
    create_project(root, example=True)
    text = build_documents(root, None, "tr-analysis", "md")[0].read_text("utf-8")
    assert "Läuft auf" not in text and "Technische Angriffsfläche" not in text


def test_svg_draws_host_and_privilege_frames(tmp_path: Path) -> None:
    sw = _product(tmp_path / "p").models["software"]
    svg = render_svg(sw)
    assert ">IPC</text>" in svg  # host frame label
    assert ">root</text>" in svg and ">user (operator)</text>" in svg
    assert 'stroke-dasharray="5 3"' in svg  # flow across the privilege boundary
