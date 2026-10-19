"""Import OSCAL catalogs, profiles and component definitions into a project (ADR-0012).

Catalogs and component definitions become project libraries
(`libraries/<slug>/`), one YAML file per entry so large catalogs stay below the
YAML file size limit and diffs stay small. A byte copy of the imported document
is kept in `libraries/<slug>/source/` so nothing of the original is lost.
Profiles become `profiles/<slug>.yaml`. Output is deterministic: re-importing
the same document rewrites identical bytes; a changed control raises the `rev`
of that entry only.
"""

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any

from threatwright.library import (
    LIBRARY_FILE,
    NAME,
    ControlRef,
    ElementType,
    I18n,
    Manifest,
    MeasureTemplate,
    load_libraries,
)
from threatwright.model.objects import OscalRef
from threatwright.model.store import LoadError, _to_yaml, read_yaml, to_plain, write_yaml
from threatwright.oscal.validate import load_valid

SOURCE_DIR = "source"
PROFILES_DIR = "profiles"
OVERRIDES_STEM = "arc-overrides"
INSERT = re.compile(r"\{\{\s*insert:\s*param,\s*([^\s}]+)\s*\}\}")
# OSCAL component type -> element kind; everything else becomes "device".
COMPONENT_KINDS = {
    "software": "process",
    "service": "process",
    "hardware": "device",
    "physical": "device",
    "interconnection": "flow",
}
_TRANSLIT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
_RESERVED = {"con", "prn", "aux", "nul"} | {f"{d}{n}" for d in ("com", "lpt") for n in range(10)}


def slug(text: str, fallback: str = "oscal") -> str:
    """Lowercase ASCII id usable as library/entry id and as file name."""
    text = unicodedata.normalize("NFKD", text.lower().translate(_TRANSLIT))
    s = re.sub(r"[^a-z0-9._-]+", "-", text.encode("ascii", "ignore").decode())
    s = re.sub(r"[-._]{2,}", "-", s).strip("-._")[:64].strip("-._")
    return s or fallback


def _filename(entry_id: str) -> str:
    # Windows refuses CON, NUL, ... even with an extension ("con.1.yaml").
    return f"x-{entry_id}.yaml" if entry_id.split(".")[0] in _RESERVED else f"{entry_id}.yaml"


def _unique(base: str, used: set[str]) -> str:
    candidate, n = base, 1
    while candidate in used:
        n += 1
        candidate = f"{base}-{n}"
    used.add(candidate)
    return candidate


def _inside(project_root: Path, folder: str, name: str) -> Path:
    """`<project>/<folder>/<name>`, refusing anything that could leave that folder."""
    if not NAME.match(name) or name.split(".")[0] in _RESERVED:
        raise ValueError(f"invalid name '{name}'")
    base = (Path(project_root) / folder).resolve()
    target = (base / name).resolve()
    if target.parent != base:
        raise ValueError(f"'{name}' escapes {base}")
    return target


def _library_dir(project_root: Path, name: str) -> Path:
    lib = _inside(project_root, "libraries", name)
    if (lib / LIBRARY_FILE).exists() and not (lib / SOURCE_DIR).is_dir():
        raise ValueError(f"library '{name}' exists and was not created by an OSCAL import")
    return lib


def _dump(data: dict[str, Any]) -> dict[str, Any]:
    """Canonical key order for entries: provenance and raw OSCAL data last."""
    tail = ("oscal_ref", "controls", "oscal_extra")
    out = {k: v for k, v in data.items() if k not in tail}
    out.update({k: data[k] for k in tail if k in data})
    return out


def _comparable(entry: dict[str, Any]) -> dict[str, Any]:
    # The source label carries the document version; it changes on every new
    # release and must not count as a content change of each entry.
    out = {k: v for k, v in entry.items() if k != "rev"}
    if isinstance(out.get("oscal_ref"), dict):
        out["oscal_ref"] = {k: v for k, v in out["oscal_ref"].items() if k != "source"}
    return out


def _write_entries(folder: Path, key: str, entries: list[dict[str, Any]]) -> None:
    """One file per entry; keep rev for unchanged entries, raise it for changed ones."""
    old: dict[str, dict[str, Any]] = {}
    for path in sorted(folder.glob("*.yaml")):
        try:
            items = to_plain(read_yaml(path)).get(key, [])
        except LoadError:
            continue
        old.update({i["id"]: i for i in items if isinstance(i, dict) and "id" in i})
    wanted: set[Path] = set()
    for entry in entries:
        prev = old.get(entry["id"])
        rev = int(prev.get("rev", 1)) if prev else 1
        if prev and _comparable(prev) != _comparable(entry):
            rev += 1
        if rev > 1:
            entry = {"id": entry["id"], "rev": rev, **{k: v for k, v in entry.items() if k != "id"}}
        path = folder / _filename(entry["id"])
        wanted.add(path)
        write_yaml(path, _to_yaml({key: [entry]}))
    for path in set(folder.glob("*.yaml")) - wanted:
        path.unlink()


def _write_library(lib: Path, file: Path, manifest: Manifest) -> None:
    source = lib / SOURCE_DIR
    source.mkdir(parents=True, exist_ok=True)
    copy = source / f"{slug(file.stem, 'document')}.json"
    for stale in source.glob("*"):
        if stale != copy and stale.is_file():
            stale.unlink()
    copy.write_bytes(file.read_bytes())
    data = {"schema_version": 1, **manifest.model_dump(mode="json", exclude_defaults=True)}
    write_yaml(lib / LIBRARY_FILE, _to_yaml(data))


def _manifest(name: str, meta: dict[str, Any], kind: str, uuid: str) -> Manifest:
    title = meta["title"]
    license_ = next(
        (p["value"] for p in meta.get("props", []) if p["name"] == "license"),
        next((lk["href"] for lk in meta.get("links", []) if lk.get("rel") == "license"), None),
    )
    parties = [p["name"] for p in meta.get("parties", []) if "name" in p]
    remarks = meta.get("remarks")
    return Manifest(
        id=name,
        version=meta["version"],
        title=I18n(de=title, en=title),
        license=license_ or "see source",
        description=I18n(de=remarks, en=remarks) if remarks else None,
        attribution=[
            f"{title} {meta['version']}",
            f"OSCAL {kind} {uuid} (OSCAL {meta['oscal-version']})",
            *parties,
        ],
    )


# --- catalog -----------------------------------------------------------------------


def _param_text(param: dict[str, Any] | None, pid: str) -> str:
    if param is None:
        return f"[{pid}]"
    if param.get("values"):
        return ", ".join(param["values"])
    if "select" in param:
        return "[" + " | ".join(param["select"].get("choice", [])) + "]"
    return f"[{param.get('label', pid)}]"


def _statement(parts: list[dict[str, Any]], params: dict[str, dict[str, Any]]) -> str:
    """Statement prose incl. nested items, parameters filled in or shown as [label]."""
    lines: list[str] = []

    def walk(part: dict[str, Any], depth: int) -> None:
        label = next((p["value"] for p in part.get("props", []) if p["name"] == "label"), "")
        prose = INSERT.sub(lambda m: _param_text(params.get(m[1]), m[1]), part.get("prose", ""))
        line = " ".join(x for x in (label, prose.strip()) if x)
        if line:
            lines.append("  " * depth + line)
        for sub in part.get("parts", []):
            walk(sub, depth + 1)

    for part in parts:
        if part["name"] == "statement":
            walk(part, 0)
    return "\n".join(lines)


def import_catalog(project_root: Path, file: Path, library_name: str | None = None) -> Path:
    file = Path(file)
    cat = load_valid(file, "catalog")
    meta = cat["metadata"]
    name = library_name or slug(meta["title"])
    lib = _library_dir(project_root, name)
    ref = {"source": f"{meta['title']} {meta['version']}", "uuid": cat["uuid"]}
    measures: list[dict[str, Any]] = []
    used: set[str] = set()

    def control(
        ctl: dict[str, Any], category: str | None, params: dict[str, Any], parent: str | None
    ) -> None:
        params = {**params, **{p["id"]: p for p in ctl.get("params", [])}}
        extra = {k: v for k, v in ctl.items() if k not in ("id", "title", "controls")}
        if parent:
            extra["parent_control"] = parent
        text = _statement(ctl.get("parts", []), params)
        entry = MeasureTemplate(
            id=_unique(slug(ctl["id"], "control"), used),
            title=I18n(de=ctl["title"], en=ctl["title"]),
            description=I18n(de=text, en=text),
            kind="organizational",
            category=category,
            oscal_ref=OscalRef.model_validate({**ref, "control_id": ctl["id"]}),
            oscal_extra=extra,
            controls=[ControlRef(catalog_uuid=cat["uuid"], control_id=ctl["id"])],
        )
        measures.append(_dump(entry.model_dump(mode="json", exclude_defaults=True)))
        for child in ctl.get("controls", []):
            control(child, category, params, ctl["id"])

    def group(grp: dict[str, Any], path: list[str], params: dict[str, Any]) -> None:
        path = [*path, " ".join(x for x in (grp.get("id"), grp["title"]) if x)]
        params = {**params, **{p["id"]: p for p in grp.get("params", [])}}
        for ctl in grp.get("controls", []):
            control(ctl, " / ".join(path), params, None)
        for sub in grp.get("groups", []):
            group(sub, path, params)

    top = {p["id"]: p for p in cat.get("params", [])}
    for ctl in cat.get("controls", []):
        control(ctl, None, top, None)
    for grp in cat.get("groups", []):
        group(grp, [], top)

    (lib / "measures").mkdir(parents=True, exist_ok=True)
    _write_entries(lib / "measures", "measures", measures)
    _write_library(lib, file, _manifest(name, meta, "catalog", cat["uuid"]))
    return lib


# --- component definition ---------------------------------------------------------------


def import_component_definition(project_root: Path, file: Path) -> Path:
    file = Path(file)
    cd = load_valid(file, "component-definition")
    meta = cd["metadata"]
    name = slug(meta["title"])
    lib = _library_dir(project_root, name)
    source = f"{meta['title']} {meta['version']}"
    elements: list[dict[str, Any]] = []
    used: set[str] = set()
    for comp in cd.get("components", []):
        extra = {k: v for k, v in comp.items() if k not in ("uuid", "title", "description")}
        ids = [
            req["control-id"]
            for impl in comp.get("control-implementations", [])
            for req in impl.get("implemented-requirements", [])
        ]
        if ids:
            extra["control_ids"] = list(dict.fromkeys(ids))
        entry = ElementType(
            id=_unique(slug(comp["title"], "component"), used),
            name=I18n(de=comp["title"], en=comp["title"]),
            kind=COMPONENT_KINDS.get(comp["type"], "device"),
            description=I18n(de=comp["description"], en=comp["description"]),
            oscal_ref=OscalRef.model_validate({"source": source, "uuid": comp["uuid"]}),
            oscal_extra=extra,
        )
        elements.append(_dump(entry.model_dump(mode="json", exclude_defaults=True)))
    (lib / "elements").mkdir(parents=True, exist_ok=True)
    _write_entries(lib / "elements", "elements", elements)
    _write_library(lib, file, _manifest(name, meta, "component-definition", cd["uuid"]))
    return lib


# --- profile ---------------------------------------------------------------------------


def _hash_matches(data: bytes, hashes: list[dict[str, Any]]) -> bool:
    for h in hashes:
        algo = h["algorithm"].lower().replace("sha3-", "sha3_").replace("-", "")
        try:
            digest = hashlib.new(algo, data, usedforsecurity=False).hexdigest()
        except ValueError:
            continue
        if digest == h["value"].lower():
            return True
    return False


def imported_libraries(project_root: Path) -> list[dict[str, Any]]:
    """Libraries created by OSCAL import, for listings (GUI settings)."""
    out: list[dict[str, Any]] = []
    for lib in sorted((Path(project_root) / "libraries").glob("*")):
        sources = sorted((lib / SOURCE_DIR).glob("*.json"))
        if not sources or not (lib / LIBRARY_FILE).exists():
            continue
        try:
            manifest = Manifest.model_validate(to_plain(read_yaml(lib / LIBRARY_FILE)))
        except Exception:  # noqa: S112 - a broken library is reported by load_libraries
            continue
        out.append(
            {
                "name": lib.name,
                "model": "component-definition" if (lib / "elements").is_dir() else "catalog",
                "title": manifest.title.en,
                "version": manifest.version,
                "license": manifest.license,
                "source": manifest.attribution[0] if manifest.attribution else None,
                "file": sources[0],
            }
        )
    return out


def _resolve(
    catalogs: list[dict[str, Any]],
    hrefs: list[str],
    hashes: list[dict[str, Any]],
    title: str | None,
) -> str | None:
    stems = {slug(h.rsplit("/", 1)[-1].removesuffix(".json")) for h in hrefs}
    for cat in catalogs:
        if (
            (hashes and _hash_matches(cat["file"].read_bytes(), hashes))
            or cat["file"].stem in stems
            or cat["name"] in stems
            or (title is not None and title == cat["title"])
        ):
            name: str = cat["name"]
            return name
    return None


def _with_ids(selections: list[dict[str, Any]]) -> list[str]:
    return [i for sel in selections for i in sel.get("with-ids", [])]


def import_profile(project_root: Path, file: Path) -> Path:
    file = Path(file)
    prof = load_valid(file, "profile")
    meta = prof["metadata"]
    name = slug(meta["title"])
    if name == OVERRIDES_STEM:
        name += "-profile"
    target = _inside(project_root, PROFILES_DIR, f"{name}.yaml")
    resources = {r["uuid"]: r for r in prof.get("back-matter", {}).get("resources", [])}
    catalogs = [c for c in imported_libraries(project_root) if c["model"] == "catalog"]
    imports = []
    for imp in prof["imports"]:
        href = imp.get("href", "")  # required by the OSCAL model, but not by the 1.2.3 JSON schema
        res = resources.get(href[1:]) if href.startswith("#") else None
        rlinks = res.get("rlinks", []) if res else []
        hrefs = [lk["href"] for lk in rlinks] if res else [href] if href else []
        hashes = [h for lk in rlinks for h in lk.get("hashes", [])]
        library = _resolve(catalogs, hrefs, hashes, res.get("title") if res else None)
        include = _with_ids(imp.get("include-controls", []))
        entry: dict[str, Any] = {
            "href": href,
            "library": library,
            "include_all": "include-all" in imp,
            "include_controls": include,
            "exclude_controls": _with_ids(imp.get("exclude-controls", [])),
        }
        if library is not None:
            libs = load_libraries([library], Path(project_root))
            known = {c.control_id for m in libs.measures.values() for c in m.controls}
            entry["missing_controls"] = [i for i in include if i not in known]
        imports.append(entry)
    set_params = {
        sp["param-id"]: sp.get("values", [])
        for sp in prof.get("modify", {}).get("set-parameters", [])
    }
    extra = {k: v for k, v in prof.items() if k not in ("uuid", "metadata")}
    doc = {
        "schema_version": 1,
        "id": name,
        "title": meta["title"],
        "version": meta["version"],
        "oscal_ref": {"source": f"{meta['title']} {meta['version']}", "uuid": prof["uuid"]},
        "imports": imports,
        "set_parameters": set_params,
        "oscal_extra": extra,
    }
    write_yaml(target, _to_yaml(doc))
    return target
