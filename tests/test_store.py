import socket
from pathlib import Path

import pytest
from conftest import ROOT

from threatwright.model.objects import Asset, Measure, Threat
from threatwright.model.schema import render_schemas
from threatwright.model.store import LoadError, Project, read_yaml


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


def test_fixture_loads_without_issues(project_dir: Path) -> None:
    project = Project.load(project_dir)
    assert project.issues == []
    main = project.models["main"]
    assert len(main.objects["elements"]) == 3
    threat = main.objects["threats"]["T-0001"]
    assert isinstance(threat, Threat)
    assert threat.assessment.impact == 4


def test_save_without_change_produces_no_diff(project_dir: Path) -> None:
    before = snapshot(project_dir)
    project = Project.load(project_dir)
    assert project.save() == []
    assert snapshot(project_dir) == before


def test_edit_touches_only_that_file_and_keeps_comments(project_dir: Path) -> None:
    before = snapshot(project_dir)
    project = Project.load(project_dir)
    threat = project.models["main"].objects["threats"]["T-0001"]
    threat.assessment.impact = 5
    written = project.save()

    rel = Path("models/main/threats/T-0001.yaml")
    assert written == [project_dir / rel]
    after = snapshot(project_dir)
    changed = {k for k in after if after[k] != before.get(k)}
    assert changed == {str(rel)}
    text = (project_dir / rel).read_text(encoding="utf-8")
    assert "  impact: 5\n" in text
    assert "# comment must survive" in text
    assert "scenario: >-" in text  # author's folded style kept


def test_new_object_is_canonical_and_stable(project_dir: Path) -> None:
    project = Project.load(project_dir)
    sub = project.models["main"]
    new_id = sub.next_id("measures")
    assert new_id == "M-0002"
    sub.objects["measures"][new_id] = Measure(
        id=new_id, title="Firmware signieren", description="Zeile 1\nZeile 2"
    )
    project.save()

    path = project_dir / "models/main/measures/M-0002.yaml"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("schema_version: 1\nid: M-0002\nuuid: ")
    assert "status:" not in text  # defaults are not written
    assert "description: |-\n  Zeile 1\n  Zeile 2\n" in text

    again = Project.load(project_dir)
    assert again.issues == []
    assert again.models["main"].objects["measures"][new_id] == sub.objects["measures"][new_id]
    assert again.save() == []


def test_removed_object_file_is_deleted(project_dir: Path) -> None:
    project = Project.load(project_dir)
    del project.models["main"].objects["questions"]["Q-0001"]
    project.save()
    assert not (project_dir / "models/main/questions/Q-0001.yaml").exists()


def test_crlf_and_bom_are_tolerated(project_dir: Path) -> None:
    path = project_dir / "models/main/assets/A-0001.yaml"
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes().replace(b"\n", b"\r\n"))
    project = Project.load(project_dir)
    assert project.issues == []
    asset = project.models["main"].objects["assets"]["A-0001"]
    assert isinstance(asset, Asset)
    asset.title = "Sicherheitsfunktionen"
    project.save()
    assert b"\r\n" not in path.read_bytes()


def test_invalid_files_are_reported_not_fatal_and_never_deleted(project_dir: Path) -> None:
    bad = project_dir / "models/main/threats/T-0099.yaml"
    bad.write_text("schema_version: 1\nid: T-0099\ntitle: x\nstride: [X]\n", encoding="utf-8")
    project = Project.load(project_dir)
    assert [i.location for i in project.issues] == ["stride.0"]
    project.save()
    assert bad.exists()


def test_id_must_match_file_name(project_dir: Path) -> None:
    (project_dir / "models/main/assets/A-0002.yaml").rename(
        project_dir / "models/main/assets/A-0003.yaml"
    )
    project = Project.load(project_dir)
    assert [i.location for i in project.issues] == ["id"]


@pytest.mark.parametrize(
    "content",
    [
        "a: " + "[" * 40 + "]" * 40,
        "a: &a [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\n"
        + "".join(
            f"{c}: &{c} [*{p}, *{p}, *{p}, *{p}, *{p}, *{p}, *{p}, *{p}]\n"
            for p, c in zip("abcdef", "bcdefg", strict=True)
        ),
    ],
    ids=["deep", "alias-bomb"],
)
def test_limits(tmp_path: Path, content: str) -> None:
    from threatwright.model.store import to_plain

    path = tmp_path / "x.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(LoadError):
        to_plain(read_yaml(path))


def test_committed_schemas_are_current() -> None:
    for filename, text in render_schemas().items():
        committed = ROOT / "schemas" / filename
        assert committed.exists(), f"run: python -m threatwright.model.schema ({filename})"
        assert committed.read_text(encoding="utf-8") == text, f"regenerate {filename}"


def test_network_guard_blocks_outbound() -> None:
    with socket.socket() as s, pytest.raises(RuntimeError):
        s.connect(("192.0.2.1", 80))
