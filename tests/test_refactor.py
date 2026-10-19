from pathlib import Path

import pytest

from threatwright.model.objects import Flow, Question, Threat
from threatwright.model.refactor import rename_id
from threatwright.model.store import Project


def test_rename_updates_references_text_layout_and_files(project_dir: Path) -> None:
    project = Project.load(project_dir)
    sub = project.models["main"]
    threat = sub.objects["threats"]["T-0001"]
    assert isinstance(threat, Threat)
    threat.scenario = "Remote I/O E-0002 is affected; E-00021 is not."
    uuid = sub.objects["elements"]["E-0002"].uuid

    updated = rename_id(project, "main", "elements", "E-0002", "E-0010")

    assert updated == 2  # flow F-0001 (target) and threat T-0001 (targets, text)
    assert sub.objects["elements"]["E-0010"].uuid == uuid
    flow = sub.objects["flows"]["F-0001"]
    assert isinstance(flow, Flow) and flow.target == "E-0010"
    threat = sub.objects["threats"]["T-0001"]
    assert isinstance(threat, Threat) and threat.targets == ["E-0010", "F-0001"]
    assert threat.scenario == "Remote I/O E-0010 is affected; E-00021 is not."
    assert "E-0010" in sub.layout.nodes and "E-0002" not in sub.layout.nodes

    project.save()
    base = project_dir / "models/main/elements"
    assert (base / "E-0010.yaml").exists() and not (base / "E-0002.yaml").exists()
    reloaded = Project.load(project_dir)
    assert reloaded.issues == [] and reloaded.save() == []


def test_rename_measure_and_question_refs(project_dir: Path) -> None:
    project = Project.load(project_dir)
    rename_id(project, "main", "threats", "T-0001", "T-0100")
    question = project.models["main"].objects["questions"]["Q-0001"]
    assert isinstance(question, Question) and question.threats == ["T-0100"]


@pytest.mark.parametrize(("new", "error"), [("E-0003", ValueError), ("bad id", ValueError)])
def test_rename_rejects_invalid(project_dir: Path, new: str, error: type[Exception]) -> None:
    project = Project.load(project_dir)
    with pytest.raises(error):
        rename_id(project, "main", "elements", "E-0001", new)
    with pytest.raises(KeyError):
        rename_id(project, "main", "elements", "E-0099", "E-0100")
