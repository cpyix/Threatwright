"""runs_on, privilege contexts, refines and the new technical element fields."""

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from threatwright import history, topology
from threatwright.model.objects import (
    Element,
    Flow,
    Listener,
    ModelMeta,
    Privilege,
    ProjectConfig,
    Zone,
)
from threatwright.model.store import Project, SubModel

COMPAT = Path(__file__).parent / "fixtures" / "compat"


def _sub(*objs: Element | Flow) -> SubModel:
    sub = SubModel(
        "software",
        ModelMeta(title="SW", zones=[Zone(id="Z-A", title="A"), Zone(id="Z-B", title="B")]),
    )
    for o in objs:
        sub.objects["elements" if isinstance(o, Element) else "flows"][o.id] = o
    return sub


def _el(id: str, kind: str = "process", **kw: object) -> Element:
    return Element.model_validate({"id": id, "title": id, "kind": kind, **kw})


def _flow(src: str, tgt: str) -> Flow:
    return Flow(id="F-0001", title="f", source=src, target=tgt)


def test_new_fields_are_optional_and_load() -> None:
    e = _el(
        "E-0002",
        runs_on="E-0001",
        privilege={"level": "root", "capabilities": ["CAP_SYS_NICE"]},
        listens_on=[
            {"protocol": "tcp", "port": 5000},
            {"protocol": "unix", "path": "/run/gui.sock"},
        ],
        authentication="none",
        memory_safe=False,
        sbom_ref={"purl": "pkg:generic/rt-control@1.0"},
        refines="main/E-0019",
    )
    assert e.listens_on[0].interfaces == "all"
    assert _el("E-0003").runs_on is None


@pytest.mark.parametrize("kind", ["datastore", "external"])
def test_host_fields_only_on_processes_and_devices(kind: str) -> None:
    with pytest.raises(ValidationError, match="runs_on"):
        _el("E-0001", kind, runs_on="E-0002")
    assert _el("E-0001", kind, refines="main/E-0001").refines == "main/E-0001"


def test_sbom_ref_not_on_external_but_on_datastore() -> None:
    with pytest.raises(ValidationError):
        _el("E-0001", "external", sbom_ref={"purl": "pkg:generic/x@1"})
    assert _el("E-0001", "datastore", sbom_ref={"cpe": "cpe:2.3:a:x:y:1:*:*:*:*:*:*:*"}).sbom_ref


@pytest.mark.parametrize(
    "spec",
    [
        {"protocol": "tcp"},
        {"protocol": "unix", "port": 1},
        {"protocol": "udp", "port": 0},
        {"protocol": "tcp", "port": 1, "path": "/x"},
    ],
)
def test_listener_address_must_fit_protocol(spec: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Listener.model_validate(spec)


@pytest.mark.parametrize("ref", ["E-0019", "main/", "Main/E-0019", "main/E-19"])
def test_refines_format(ref: str) -> None:
    with pytest.raises(ValidationError):
        _el("E-0001", refines=ref)


def test_process_inherits_zone_of_host_transitively() -> None:
    sub = _sub(
        _el("E-0001", "device", zone="Z-A"),
        _el("E-0002", "device", runs_on="E-0001"),  # virtual machine
        _el("E-0003", runs_on="E-0002"),
        _el("E-0004", runs_on="E-0001", zone="Z-B"),
    )
    els = sub.objects["elements"]
    assert topology.effective_zone(sub, els["E-0003"]) == "Z-A"  # type: ignore[arg-type]
    assert topology.effective_zone(sub, els["E-0004"]) == "Z-B"  # type: ignore[arg-type]
    assert [e.id for e in topology.hosted(sub, "E-0001")] == ["E-0002", "E-0003", "E-0004"]


def test_boundary_zone_and_privilege() -> None:
    host = _el("E-0001", "device", zone="Z-A")
    root = _el("E-0002", runs_on="E-0001", privilege={"level": "root"})
    gui = _el("E-0003", runs_on="E-0001", privilege={"level": "user", "account": "operator"})
    other = _el("E-0004", runs_on="E-0001", privilege={"level": "root"})
    remote = _el("E-0005", "external", zone="Z-B")
    sub = _sub(host, root, gui, other, remote)
    assert topology.boundary(sub, _flow("E-0003", "E-0002")) == "privilege"
    assert topology.boundary(sub, _flow("E-0004", "E-0002")) is None  # same context
    assert topology.boundary(sub, _flow("E-0005", "E-0002")) == "zone"
    assert topology.boundary(sub, _flow("E-0001", "E-0002")) is None  # host itself: no context
    assert topology.more_privileged(gui, root) is root


def test_runs_on_cycle_detected_and_chain_terminates() -> None:
    sub = _sub(_el("E-0001", "device", runs_on="E-0002"), _el("E-0002", "device", runs_on="E-0001"))
    a = sub.objects["elements"]["E-0001"]
    assert topology.runs_on_cycle(sub, a)  # type: ignore[arg-type]
    assert [h.id for h in topology.host_chain(sub, a)] == ["E-0002"]  # type: ignore[arg-type]


def test_refines_resolution_and_parent_model(tmp_path: Path) -> None:
    project = Project(root=tmp_path, config=ProjectConfig(name="p"))
    main = SubModel("main", ModelMeta(title="Main"))
    main.objects["elements"]["E-0001"] = _el("E-0001", "device")
    sw = _sub(_el("E-0001", "device", refines="main/E-0001"))
    project.models = {"main": main, "software": sw}
    assert topology.resolve_refines(project, "main/E-0001") is main.objects["elements"]["E-0001"]
    assert topology.resolve_refines(project, "main/E-0002") is None
    assert topology.parent_model(project, sw) == "main"
    assert topology.submodels(project, "main") == [sw]
    assert topology.refined_by(project, "main", "E-0001")[0][0] is sw


def test_old_project_with_new_fields_round_trips(tmp_path: Path) -> None:
    """No schema bump (ADR-0015): a v0.4.0 project gains the fields, saves and reloads unchanged."""
    root = tmp_path / "p"
    shutil.copytree(COMPAT / "v0.4.0", root)
    project = Project.load(root)
    sub = next(iter(project.models.values()))
    el = next(
        e
        for e in sub.objects["elements"].values()
        if isinstance(e, Element) and e.kind in ("process", "device")
    )
    el.privilege = Privilege(level="service")
    el.authentication = "key"
    project.save()
    reloaded = Project.load(root)
    assert reloaded.issues == [] and reloaded.migrated == []
    assert history.dump(reloaded.models) == history.dump(project.models)
    text = (root / "models" / sub.name / "elements" / f"{el.id}.yaml").read_text()
    assert "schema_version: 1" in text and "authentication: key" in text
