from pathlib import Path

from threatwright.model.delete import delete_with_refs, deletion_plan
from threatwright.model.objects import Question, Threat
from threatwright.model.store import Project


def test_cascade_removes_flows_threats_measures_and_refs(project_dir: Path) -> None:
    project = Project.load(project_dir)
    sub = project.models["main"]
    # T-0001 targets only E-0002 and its flow F-0001, and is the only user of M-0001
    plan = deletion_plan(sub, "elements", "E-0002")
    assert plan == {"flows": ["F-0001"], "threats": ["T-0001"], "measures": ["M-0001"]}

    delete_with_refs(sub, "elements", "E-0002", cascade=True)

    for coll, oid in [
        ("elements", "E-0002"),
        ("flows", "F-0001"),
        ("threats", "T-0001"),
        ("measures", "M-0001"),
    ]:
        assert oid not in sub.objects[coll]
    assert "E-0002" not in sub.layout.nodes
    question = sub.objects["questions"]["Q-0001"]
    assert isinstance(question, Question) and question.threats == []
    project.save()
    assert Project.load(project_dir).issues == []


def test_without_cascade_threats_stay_and_lose_the_reference(project_dir: Path) -> None:
    sub = Project.load(project_dir).models["main"]
    delete_with_refs(sub, "elements", "E-0002", cascade=False)
    threat = sub.objects["threats"]["T-0001"]
    assert isinstance(threat, Threat) and threat.targets == [] and threat.measures == ["M-0001"]
    assert "F-0001" not in sub.objects["flows"]  # a flow cannot outlive its end


def test_threat_with_other_targets_is_not_planned(project_dir: Path) -> None:
    sub = Project.load(project_dir).models["main"]
    # T-0001 also targets E-0002, which stays
    assert deletion_plan(sub, "elements", "E-0001") == {
        "flows": ["F-0001"],
        "threats": [],
        "measures": [],
    }
    delete_with_refs(sub, "elements", "E-0001", cascade=True)
    threat = sub.objects["threats"]["T-0001"]
    assert isinstance(threat, Threat) and threat.targets == ["E-0002"]
