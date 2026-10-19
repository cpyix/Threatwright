import json
from pathlib import Path
from typing import Any

import pytest
from referencing.exceptions import NoSuchResource

from threatwright.library import load_libraries
from threatwright.oscal import validate
from threatwright.oscal.imports import (
    import_catalog,
    import_component_definition,
    import_profile,
    imported_libraries,
    slug,
)
from threatwright.oscal.validate import OscalError, validate_oscal

FIXTURES = Path(__file__).parent / "fixtures" / "oscal"
CATALOG = FIXTURES / "synthetic-arc-catalog.json"
PROFILE = FIXTURES / "synthetic-profile.json"
COMPONENT = FIXTURES / "synthetic-component.json"
GRUNDSCHUTZ = FIXTURES / "grundschutz-excerpt.json"


def load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def dump(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


# --- validation ------------------------------------------------------------------------


@pytest.mark.parametrize("path", [CATALOG, PROFILE, COMPONENT, GRUNDSCHUTZ])
def test_valid_documents(path: Path) -> None:
    assert validate_oscal(path) == []


@pytest.mark.parametrize(
    ("path", "model"),
    [(CATALOG, "catalog"), (PROFILE, "profile"), (COMPONENT, "component-definition")],
)
def test_invalid_documents(tmp_path: Path, path: Path, model: str) -> None:
    data = load(path)
    del data[model]["uuid"]
    data[model]["metadata"]["last-modified"] = "yesterday"
    issues = validate_oscal(dump(tmp_path / "bad.json", data))
    assert {i.code for i in issues} == {"oscal-schema"}
    assert {i.location for i in issues} == {model, f"{model}.metadata.last-modified"}


def test_unicode_token_pattern(tmp_path: Path) -> None:
    data = load(CATALOG)
    ctl = data["catalog"]["groups"][0]["groups"][0]["controls"][0]
    ctl["id"] = "Ä-1"  # \p{L} in the NIST pattern
    assert validate_oscal(dump(tmp_path / "ok.json", data)) == []
    ctl["id"] = "1 bad"
    (issue,) = validate_oscal(dump(tmp_path / "bad.json", data))
    assert issue.location.endswith("controls.0.id")


@pytest.mark.parametrize("name", ["c.xml", "c.yaml", "c.yml"])
def test_xml_yaml_unsupported(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    path.write_text("catalog: {}", encoding="utf-8")
    (issue,) = validate_oscal(path)
    assert issue.code == "oscal-format" and "not supported" in issue.message


def test_not_json_and_bad_roots(tmp_path: Path) -> None:
    path = tmp_path / "x.json"
    path.write_text("<catalog/>", encoding="utf-8")
    assert "not supported" in validate_oscal(path)[0].message
    assert validate_oscal(dump(path, {"a": {}, "b": {}}))[0].code == "oscal-format"
    assert validate_oscal(dump(path, {"foo": {}}))[0].code == "oscal-unsupported"
    assert validate_oscal(tmp_path / "missing.json")[0].message == "file not found"


def test_other_model_unsupported_but_validated(tmp_path: Path) -> None:
    issues = validate_oscal(dump(tmp_path / "ssp.json", {"system-security-plan": {}}))
    assert issues[0].code == "oscal-unsupported"
    assert any(i.code == "oscal-schema" for i in issues[1:])


def test_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validate, "MAX_BYTES", 10)
    (issue,) = validate_oscal(CATALOG)
    assert issue.code == "oscal-too-large"


def test_no_remote_schema_retrieval() -> None:
    with pytest.raises(NoSuchResource):
        validate._no_retrieve("https://example.org/schema.json")


def test_import_rejects_invalid_and_wrong_model(tmp_path: Path) -> None:
    with pytest.raises(OscalError):
        import_catalog(tmp_path, PROFILE)
    data = load(CATALOG)
    del data["catalog"]["metadata"]
    with pytest.raises(OscalError):
        import_catalog(tmp_path, dump(tmp_path / "bad.json", data))
    assert not (tmp_path / "libraries").exists()


# --- catalog ----------------------------------------------------------------------------


def test_catalog_import_loads_as_library(tmp_path: Path) -> None:
    lib = import_catalog(tmp_path, CATALOG)
    assert lib == (tmp_path / "libraries" / "synthetic-arc-catalog").resolve()
    libs = load_libraries([lib.name], tmp_path)
    assert libs.issues == []
    assert sorted(libs.measures) == ["arc-1", "arc-1.1", "arc-2", "arc-3", "arc-4", "arc-5"]
    m = libs.measures["arc-1"]
    assert m.kind == "organizational"
    assert m.category == "ARC Synthetic risk-based controls / ARC.FLD Field"
    assert m.description.en == (
        "The PwDE MUST check field interfaces every 24 hours.\n"
        "  a. Unused interfaces MUST be disabled."
    )
    assert m.oscal_ref is not None and m.oscal_ref.control_id == "ARC-1"
    assert m.oscal_ref.source == "Synthetic ARC catalog 1.0"
    assert str(m.oscal_ref.uuid) == "6f1c2a3b-0d4e-4f5a-8b6c-7d8e9f0a1b2c"
    assert [(c.catalog_uuid, c.control_id) for c in m.controls] == [
        ("6f1c2a3b-0d4e-4f5a-8b6c-7d8e9f0a1b2c", "ARC-1")
    ]
    assert libs.measures["arc-1.1"].oscal_extra["parent_control"] == "ARC-1"
    assert (
        libs.measures["arc-2"].description.en == "The PwDE MUST check for updates [daily | weekly]."
    )
    assert libs.measures["arc-3"].description.en.endswith("[recovery time].")
    manifest = libs.manifests[lib.name]
    assert (manifest.version, manifest.license) == ("1.0", "CC0-1.0")
    assert (lib / "source" / "synthetic-arc-catalog.json").read_bytes() == CATALOG.read_bytes()
    (listed,) = imported_libraries(tmp_path)
    assert listed["model"] == "catalog" and listed["source"] == "Synthetic ARC catalog 1.0"


def test_grundschutz_excerpt_imports(tmp_path: Path) -> None:
    lib = import_catalog(tmp_path, GRUNDSCHUTZ, library_name="gspp")
    libs = load_libraries(["gspp"], tmp_path)
    assert libs.issues == []
    assert libs.manifests["gspp"].license == "see source"
    assert "gc.3.1.1" in libs.measures
    assert "[einem anerkannten Standard]" in libs.measures["gc.1.1"].description.de
    assert lib.name == "gspp"


def test_reimport_is_byte_identical(tmp_path: Path) -> None:
    import_catalog(tmp_path, CATALOG)
    before = snapshot(tmp_path)
    import_catalog(tmp_path, CATALOG)
    assert snapshot(tmp_path) == before


def test_new_catalog_version_bumps_changed_entries_only(tmp_path: Path) -> None:
    lib = import_catalog(tmp_path, CATALOG)
    data = load(CATALOG)
    data["catalog"]["metadata"]["version"] = "1.1"
    upd = data["catalog"]["groups"][0]["groups"][1]["controls"]
    upd[0]["parts"][0]["prose"] = "The PwDE MUST check for updates automatically."
    del upd[-1]  # ARC-5 removed
    import_catalog(tmp_path, dump(tmp_path / "synthetic-arc-catalog.json", data))
    libs = load_libraries([lib.name], tmp_path)
    assert libs.issues == []
    assert {k: m.rev for k, m in libs.measures.items()} == {
        "arc-1": 1,
        "arc-1.1": 1,
        "arc-2": 2,
        "arc-3": 1,
        "arc-4": 1,
    }
    assert libs.measures["arc-1"].oscal_ref.source == "Synthetic ARC catalog 1.1"  # type: ignore[union-attr]
    assert libs.manifests[lib.name].version == "1.1"
    # a third import of the same version changes nothing
    before = snapshot(tmp_path / "libraries")
    import_catalog(tmp_path, tmp_path / "synthetic-arc-catalog.json")
    assert snapshot(tmp_path / "libraries") == before


def test_nothing_lost(tmp_path: Path) -> None:
    """Every control can be rebuilt from its library entry (oscal_extra + id/title)."""
    lib = import_catalog(tmp_path, GRUNDSCHUTZ)
    entries = {
        m.oscal_ref.control_id: m  # type: ignore[union-attr]
        for m in load_libraries([lib.name], tmp_path).measures.values()
    }

    def rebuild(control_id: str) -> dict[str, Any]:
        m = entries[control_id]
        extra = {k: v for k, v in m.oscal_extra.items() if k != "parent_control"}
        out = {"id": control_id, "title": m.title.de, **extra}
        children = [
            rebuild(c)
            for c, e in entries.items()
            if e.oscal_extra.get("parent_control") == control_id
        ]
        if children:
            out["controls"] = children
        return out

    def controls(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [c for g in groups for c in g.get("controls", []) + controls(g.get("groups", []))]

    original = controls(load(GRUNDSCHUTZ)["catalog"]["groups"])
    assert len(original) == 3
    for ctl in original:
        assert rebuild(ctl["id"]) == ctl


@pytest.mark.parametrize("name", ["../evil", "..", "a/b", "con", "Upper", ""])
def test_library_name_cannot_escape(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError):
        import_catalog(tmp_path, CATALOG, library_name=name or "-")
    assert not (tmp_path.parent / "evil").exists()


def test_title_slug_stays_inside(tmp_path: Path) -> None:
    data = load(CATALOG)
    data["catalog"]["metadata"]["title"] = "../../Über/../evil"
    lib = import_catalog(tmp_path, dump(tmp_path / "c.json", data))
    assert lib.parent == (tmp_path / "libraries").resolve()
    assert lib.name == "ueber-evil"
    assert slug("...") == "oscal"


def test_refuses_to_overwrite_hand_written_library(tmp_path: Path) -> None:
    lib = tmp_path / "libraries" / "synthetic-arc-catalog"
    lib.mkdir(parents=True)
    (lib / "library.yaml").write_text("id: x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not created by an OSCAL import"):
        import_catalog(tmp_path, CATALOG)


# --- profile and component --------------------------------------------------------------


def test_profile_import(tmp_path: Path) -> None:
    import_catalog(tmp_path, CATALOG)
    path = import_profile(tmp_path, PROFILE)
    assert path == (tmp_path / "profiles" / "synthetic-field-profile.yaml").resolve()
    from threatwright.model.store import read_yaml, to_plain

    doc = to_plain(read_yaml(path))
    (imp,) = doc["imports"]
    assert imp["library"] == "synthetic-arc-catalog"
    assert imp["include_controls"] == ["ARC-1", "ARC-9"]
    assert imp["exclude_controls"] == ["ARC-1.1"]
    assert imp["missing_controls"] == ["ARC-9"]
    assert doc["set_parameters"] == {"arc-1_prm1": ["12 hours"]}
    assert doc["oscal_extra"]["merge"] == {"as-is": True}
    before = snapshot(tmp_path)
    import_profile(tmp_path, PROFILE)
    assert snapshot(tmp_path) == before


def test_profile_without_imported_catalog(tmp_path: Path) -> None:
    from threatwright.model.store import read_yaml, to_plain

    doc = to_plain(read_yaml(import_profile(tmp_path, PROFILE)))
    assert doc["imports"][0]["library"] is None
    assert "missing_controls" not in doc["imports"][0]


def test_profile_resolves_by_hash(tmp_path: Path) -> None:
    import hashlib

    import_catalog(tmp_path, CATALOG)
    data = load(PROFILE)
    rlink = data["profile"]["back-matter"]["resources"][0]["rlinks"][0]
    rlink["href"] = "https://example.org/renamed.json"
    rlink["hashes"] = [
        {"algorithm": "SHA-256", "value": hashlib.sha256(CATALOG.read_bytes()).hexdigest()}
    ]
    from threatwright.model.store import read_yaml, to_plain

    doc = to_plain(read_yaml(import_profile(tmp_path, dump(tmp_path / "p.json", data))))
    assert doc["imports"][0]["library"] == "synthetic-arc-catalog"


def test_component_import(tmp_path: Path) -> None:
    lib = import_component_definition(tmp_path, COMPONENT)
    libs = load_libraries([lib.name], tmp_path)
    assert libs.issues == []
    kinds = {k: e.kind for k, e in libs.elements.items()}
    assert kinds == {
        "remote-i-o-module": "device",
        "engineering-tool": "process",
        "update-policy": "device",
    }
    rio = libs.elements["remote-i-o-module"]
    assert rio.oscal_extra["control_ids"] == ["ARC-1", "ARC-4"]
    assert rio.oscal_extra["type"] == "hardware"
    assert str(rio.oscal_ref.uuid) == "4d5e6f70-8192-4a34-9c5d-6e7f80910213"  # type: ignore[union-attr]
    assert rio.description is not None and rio.description.en.startswith("Generic field device")
    assert imported_libraries(tmp_path)[0]["model"] == "component-definition"
    before = snapshot(tmp_path)
    import_component_definition(tmp_path, COMPONENT)
    assert snapshot(tmp_path) == before
