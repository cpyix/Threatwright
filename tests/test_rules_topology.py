"""Rules for runs_on, refines, privilege boundaries, exposed services, host takeover, sbom_ref."""

from pathlib import Path
from typing import Any

import pytest

from threatwright.model.objects import (
    Assessment,
    Asset,
    Element,
    Flow,
    ModelMeta,
    ProjectConfig,
    Threat,
    Zone,
)
from threatwright.model.store import Project, SubModel
from threatwright.rules import validate


def _project(tmp_path: Path, **models: list[Any]) -> Project:
    project = Project(root=tmp_path, config=ProjectConfig(name="p"))
    for name, objs in models.items():
        sub = SubModel(name, ModelMeta(title=name, zones=[Zone(id="Z-A", title="A")]))
        for o in objs:
            coll = {Element: "elements", Flow: "flows", Asset: "assets", Threat: "threats"}[type(o)]
            sub.objects[coll][o.id] = o
        project.models[name] = sub
    return project


def el(id: str, kind: str = "process", **kw: Any) -> Element:
    return Element.model_validate({"id": id, "title": id, "kind": kind, "zone": "Z-A", **kw})


def threat(id: str, targets: list[str], stride: list[str], **kw: Any) -> Threat:
    return Threat.model_validate(
        {"id": id, "title": id, "targets": targets, "stride": stride, **kw}
    )


def found(project: Project, code: str) -> set[tuple[str | None, str | None]]:
    return {(i.model, i.object_id) for i in validate(project) if i.code == code}


def test_runs_on_must_name_a_device(tmp_path: Path) -> None:
    p = _project(
        tmp_path,
        main=[
            el("E-0001", "device"),
            el("E-0002", runs_on="E-0001"),
            el("E-0003", runs_on="E-0002"),  # a process is no host
            el("E-0004", runs_on="E-0099"),
        ],
    )
    assert found(p, "runs-on-invalid") == {("main", "E-0003"), ("main", "E-0004")}


def test_runs_on_cycle(tmp_path: Path) -> None:
    p = _project(
        tmp_path,
        main=[el("E-0001", "device", runs_on="E-0002"), el("E-0002", "device", runs_on="E-0001")],
    )
    assert found(p, "runs-on-cycle") == {("main", "E-0001"), ("main", "E-0002")}
    ok = _project(tmp_path, main=[el("E-0001", "device"), el("E-0002", "device", runs_on="E-0001")])
    assert found(ok, "runs-on-cycle") == set()


def test_refines_unresolved_and_own_model(tmp_path: Path) -> None:
    p = _project(
        tmp_path,
        main=[el("E-0001", "device")],
        software=[
            el("E-0001", "device", refines="main/E-0001"),
            el("E-0002", refines="main/E-0042"),
            el("E-0003", refines="software/E-0001"),
            el("E-0004", refines="nope/E-0001"),
        ],
    )
    assert found(p, "refines-unresolved") == {
        ("software", "E-0002"),
        ("software", "E-0003"),
        ("software", "E-0004"),
    }


def test_refines_multiple_parents(tmp_path: Path) -> None:
    p = _project(
        tmp_path,
        main=[el("E-0001", "device")],
        other=[el("E-0001", "device")],
        software=[el("E-0001", refines="main/E-0001"), el("E-0002", refines="other/E-0001")],
    )
    assert found(p, "refines-multiple-parents") == {("software", "E-0001"), ("software", "E-0002")}


def test_refines_cycle(tmp_path: Path) -> None:
    p = _project(
        tmp_path,
        main=[el("E-0001", "device", refines="software/E-0001")],
        software=[el("E-0001", "device", refines="main/E-0001")],
    )
    assert found(p, "refines-cycle") == {("main", "E-0001"), ("software", "E-0001")}


@pytest.mark.parametrize(
    ("auth", "interfaces", "stride", "expected"),
    [
        (None, "all", [], True),
        ("unknown", "all", ["T"], True),
        ("none", "all", ["S"], False),  # threat with S on the element
        ("none", "all", ["E"], False),
        ("none", "loopback", [], False),
        ("key", "all", [], False),
    ],
)
def test_exposed_service_unauthenticated(
    tmp_path: Path, auth: str | None, interfaces: str, stride: list[str], expected: bool
) -> None:
    svc = el(
        "E-0001",
        listens_on=[{"protocol": "tcp", "port": 4840, "interfaces": interfaces}],
        authentication=auth,
    )
    objs: list[Any] = [svc] + ([threat("T-0001", ["E-0001"], stride)] if stride else [])
    p = _project(tmp_path, main=objs)
    assert bool(found(p, "exposed-service-unauthenticated")) is expected


def _boundary_model(*extra: Any, **flow: Any) -> list[Any]:
    return [
        el("E-0001", "device"),
        el("E-0002", runs_on="E-0001", privilege={"level": "root"}),
        el("E-0003", runs_on="E-0001", privilege={"level": "user", "account": "operator"}),
        Flow.model_validate(
            {"id": "F-0001", "title": "ipc", "source": "E-0003", "target": "E-0002", **flow}
        ),
        *extra,
    ]


def test_privilege_boundary_gap(tmp_path: Path) -> None:
    p = _project(tmp_path, main=_boundary_model())
    issues = [i for i in validate(p) if i.code == "privilege-boundary-gap"]
    assert {i.location for i in issues} == {"stride.S", "stride.E"}
    # E on the more privileged side, S on the flow itself
    covered = _boundary_model(
        threat("T-0001", ["E-0002"], ["E"]), threat("T-0002", ["F-0001"], ["S"])
    )
    assert found(_project(tmp_path, main=covered), "privilege-boundary-gap") == set()
    # E on the less privileged side does not count; S marked as not relevant does
    partly = _boundary_model(threat("T-0001", ["E-0003"], ["E"]), stride_not_relevant={"S": "why"})
    issues = [
        i for i in validate(_project(tmp_path, main=partly)) if i.code == "privilege-boundary-gap"
    ]
    assert [i.location for i in issues] == ["stride.E"]


def test_same_context_is_no_privilege_boundary(tmp_path: Path) -> None:
    objs = _boundary_model()
    objs[2] = el("E-0003", runs_on="E-0001", privilege={"level": "root"})
    assert found(_project(tmp_path, main=objs), "privilege-boundary-gap") == set()


def _takeover(impact: int, listed: bool) -> list[Any]:
    safety = Asset(id="A-0001", title="Safety", asset_class="Functions.Safety")  # A = 5
    return [
        el("E-0001", "device"),
        el("E-0002", runs_on="E-0001"),
        safety,
        threat("T-0001", ["E-0002"], ["D"], assets=["A-0001"]),  # the process handles A-0001
        threat(
            "T-0002",
            ["E-0001"],
            ["E"],
            assets=["A-0001"] if listed else [],
            assessment=Assessment(impact=impact),
        ),
    ]


def test_host_takeover_understated(tmp_path: Path) -> None:
    assert found(_project(tmp_path, main=_takeover(2, False)), "host-takeover-understated") == {
        ("main", "T-0002")
    }
    assert found(_project(tmp_path, main=_takeover(2, True)), "host-takeover-understated") == set()
    assert found(_project(tmp_path, main=_takeover(5, False)), "host-takeover-understated") == set()


def test_host_takeover_through_refined_element(tmp_path: Path) -> None:
    safety = Asset(id="A-0001", title="Safety", asset_class="Functions.Safety")
    p = _project(
        tmp_path,
        main=[
            el("E-0001", "device"),
            threat("T-0001", ["E-0001"], ["E"], assessment=Assessment(impact=3)),
        ],
        software=[
            el("E-0001", "device", refines="main/E-0001"),
            el("E-0002", runs_on="E-0001"),
            safety,
            threat("T-0001", ["E-0002"], ["D"], assets=["A-0001"]),
        ],
    )
    issues = [i for i in validate(p) if i.code == "host-takeover-understated"]
    assert [(i.model, i.object_id) for i in issues] == [("main", "T-0001")]
    assert "software/E-0002" in issues[0].message


@pytest.mark.parametrize(
    ("ref", "ok"),
    [
        ({"purl": "pkg:deb/debian/openssh-server@9.2p1"}, True),
        ({"purl": "pkg:generic/rt-control@1.0?arch=arm64"}, True),
        ({"purl": "openssh@9.2"}, False),
        ({"purl": "pkg:/x"}, False),
        ({"cpe": "cpe:2.3:a:openbsd:openssh:9.2:p1:*:*:*:*:*:*"}, True),
        ({"cpe": "cpe:/a:openbsd:openssh:9.2"}, True),
        ({"cpe": "cpe:2.3:a:openbsd:openssh"}, False),
        ({"cpe": "openssh"}, False),
    ],
)
def test_sbom_ref_format(tmp_path: Path, ref: dict[str, str], ok: bool) -> None:
    p = _project(tmp_path, main=[el("E-0001", sbom_ref=ref)])
    assert (found(p, "sbom-ref-invalid") == set()) is ok


def _refined(main_threat_ref: str | None, sub_threat_ref: str | None) -> dict[str, list[Any]]:
    return {
        "main": [
            el("E-0001", "device"),
            threat(
                "T-0001", ["E-0001"], ["S", "T", "R", "I", "D", "E"], library_ref=main_threat_ref
            ),
        ],
        "software": [
            el("E-0001", "device", refines="main/E-0001"),
            el("E-0002", runs_on="E-0001"),
            threat(
                "T-0001", ["E-0002"], ["S", "T", "R", "I", "D", "E"], library_ref=sub_threat_ref
            ),
        ],
    }


def test_duplicate_assessment(tmp_path: Path) -> None:
    dup = _refined(
        "lib:ot/threat/privilege-escalation-linux@1", "lib:ot/threat/privilege-escalation-linux@2"
    )
    assert found(_project(tmp_path, **dup), "duplicate-assessment") == {("software", "T-0001")}
    other = _refined(
        "lib:ot/threat/privilege-escalation-linux@1", "lib:ot/threat/usb-malware-autorun@1"
    )
    assert found(_project(tmp_path, **other), "duplicate-assessment") == set()


def test_refined_and_refining_elements_share_coverage(tmp_path: Path) -> None:
    p = _project(
        tmp_path,
        main=[el("E-0001", "device")],
        software=[
            el("E-0001", "device", refines="main/E-0001"),
            el("E-0002", runs_on="E-0001"),
            threat("T-0001", ["E-0002"], ["S", "T", "R", "I", "D", "E"]),
        ],
    )
    gaps = {
        (i.model, i.object_id)
        for i in validate(p)
        if i.code in ("coverage-gap", "element-without-threat")
    }
    assert ("main", "E-0001") not in gaps  # analysed in the sub-model
    assert ("software", "E-0002") not in gaps
    assert ("software", "E-0001") in gaps  # nothing on the host itself, nor on the refined element


def test_cra_requirements_counted_once_per_product(tmp_path: Path) -> None:
    p = _project(
        tmp_path,
        main=[el("E-0001", "device"), threat("T-0001", ["E-0001"], ["T"])],
        software=[
            el("E-0001", "device", refines="main/E-0001"),
            threat("T-0001", ["E-0001"], ["T"], cra_refs=["AI-I-2-a"]),
        ],
    )
    uncovered = [i for i in validate(p) if i.code == "cra-requirement-uncovered"]
    assert {i.model for i in uncovered} == {"main"}  # never on the sub-model
    assert not any("AI-I-2-a " in i.message for i in uncovered)  # covered by the sub-model
