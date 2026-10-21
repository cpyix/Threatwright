"""SBOMs and vulnerability statements as project files, offline (ADR-0007, ADR-0016).

`sbom/` holds CycloneDX JSON SBOMs; an element lists the files describing its
software in `sbom`. `vulnerabilities/` holds CycloneDX VEX/VDR or CSAF 2.x JSON
documents; vulnerabilities embedded in an SBOM count as well. Components and
statements are matched by package URL (purl, without qualifiers and subpath).
A vulnerability that affects a component of an element needs a threat listing
its id in `vulnerabilities` (rule vulnerability-untreated).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from threatwright.model.objects import Element, Threat
from threatwright.model.store import Issue, Project, SubModel

SBOM_DIR = "sbom"
VULN_DIR = "vulnerabilities"
MAX_BYTES = 32 << 20
State = Literal["affected", "under_investigation", "fixed", "not_affected"]
OPEN_STATES: frozenset[State] = frozenset({"affected", "under_investigation"})

# CycloneDX analysis.state -> state; no analysis means "affected"
CDX_STATE: dict[str, State] = {
    "exploitable": "affected",
    "in_triage": "under_investigation",
    "not_affected": "not_affected",
    "false_positive": "not_affected",
    "resolved": "fixed",
    "resolved_with_pedigree": "fixed",
}
# CSAF product_status list -> state
CSAF_STATE: dict[str, State] = {
    "known_affected": "affected",
    "first_affected": "affected",
    "last_affected": "affected",
    "under_investigation": "under_investigation",
    "fixed": "fixed",
    "first_fixed": "fixed",
    "known_not_affected": "not_affected",
}


class SbomError(ValueError):
    pass


@dataclass(frozen=True)
class Component:
    purl: str
    name: str
    version: str | None


@dataclass(frozen=True)
class Statement:
    """One document's statement about one vulnerability and one component."""

    vuln: str
    purl: str
    state: State
    source: str  # file, relative to the project
    detail: str | None = None


@dataclass
class Finding:
    """A vulnerability that concerns a component of an element."""

    vuln: str
    element: str
    purl: str
    state: State
    sources: list[str] = field(default_factory=list)
    detail: str | None = None
    threats: list[str] = field(default_factory=list)

    @property
    def open(self) -> bool:
        return self.state in OPEN_STATES


def normalize(purl: str) -> str:
    """purl without qualifiers and subpath; the type is case-insensitive."""
    core = purl.split("#", 1)[0].split("?", 1)[0].strip()
    head, _, rest = core.partition("/")
    return f"{head.lower()}/{rest}" if rest else core


def _read(path: Path) -> dict[str, Any]:
    if path.stat().st_size > MAX_BYTES:
        raise SbomError(f"larger than {MAX_BYTES >> 20} MB")
    try:
        doc = json.loads(path.read_bytes().decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise SbomError(f"invalid JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise SbomError("top level must be a JSON object")
    return doc


def _obj(value: Any) -> dict[str, Any]:
    """Untrusted JSON: a mapping, or empty when the document has something else there."""
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _walk(items: Any) -> list[dict[str, Any]]:
    """CycloneDX components, including nested ones."""
    out: list[dict[str, Any]] = []
    stack = list(_list(items))
    while stack:
        c = stack.pop()
        if isinstance(c, dict):
            out.append(c)
            stack.extend(_list(c.get("components")))
    return out


def _cyclonedx_components(doc: dict[str, Any]) -> list[Component]:
    found = {}
    for c in _walk(doc.get("components")):
        if isinstance(c.get("purl"), str) and c["purl"].startswith("pkg:"):
            purl = normalize(c["purl"])
            found[purl] = Component(purl, str(c.get("name") or purl), c.get("version"))
    return sorted(found.values(), key=lambda c: c.purl)


def _cyclonedx_statements(doc: dict[str, Any], source: str) -> list[Statement]:
    refs = {
        c["bom-ref"]: normalize(c["purl"])
        for c in _walk(doc.get("components"))
        if isinstance(c.get("bom-ref"), str) and isinstance(c.get("purl"), str)
    }
    out = []
    for v in _list(doc.get("vulnerabilities")):
        if not isinstance(v, dict) or not isinstance(v.get("id"), str):
            continue
        analysis = _obj(v.get("analysis"))
        state: State = CDX_STATE.get(str(analysis.get("state")), "affected")
        detail = analysis.get("detail") or analysis.get("justification") or v.get("description")
        detail = detail if isinstance(detail, str) else None
        for a in _list(v.get("affects")):
            ref = _obj(a).get("ref")
            if not isinstance(ref, str):
                continue
            purl = refs.get(ref) or (normalize(ref) if ref.startswith("pkg:") else None)
            if purl:
                out.append(Statement(v["id"], purl, state, source, detail))
    return out


def _csaf_products(tree: Any) -> dict[str, str]:
    """CSAF product_id -> purl from the product tree."""
    out: dict[str, str] = {}
    stack: list[Any] = [tree]
    while stack:  # products sit in branches, full_product_names and relationships
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
            continue
        if not isinstance(node, dict):
            continue
        stack.extend(v for v in node.values() if isinstance(v, dict | list))
        helper = node.get("product_identification_helper")
        if isinstance(node.get("product_id"), str) and isinstance(helper, dict):
            purls = [helper.get("purl"), *_list(helper.get("purls"))]
            purl = next((p for p in purls if isinstance(p, str) and p.startswith("pkg:")), None)
            if purl:
                out[node["product_id"]] = normalize(purl)
    return out


def _csaf_statements(doc: dict[str, Any], source: str) -> list[Statement]:
    products = _csaf_products(doc.get("product_tree"))
    out = []
    for v in _list(doc.get("vulnerabilities")):
        if not isinstance(v, dict):
            continue
        ids = [v.get("cve"), *(_obj(i).get("text") for i in _list(v.get("ids")))]
        vuln = next((i for i in ids if isinstance(i, str) and i), None)
        if vuln is None:
            continue
        status = _obj(v.get("product_status"))
        for key, state in CSAF_STATE.items():
            for pid in _list(status.get(key)):
                if isinstance(pid, str) and pid in products:
                    out.append(Statement(vuln, products[pid], state, source))
    return out


def read_sbom(path: Path) -> list[Component]:
    doc = _read(path)
    if doc.get("bomFormat") != "CycloneDX":
        raise SbomError("not a CycloneDX JSON SBOM (bomFormat: CycloneDX)")
    return _cyclonedx_components(doc)


def read_statements(path: Path, source: str) -> list[Statement]:
    doc = _read(path)
    if doc.get("bomFormat") == "CycloneDX":
        return _cyclonedx_statements(doc, source)
    if "csaf_version" in _obj(doc.get("document")):
        return _csaf_statements(doc, source)
    raise SbomError("neither CycloneDX (bomFormat) nor CSAF (document.csaf_version)")


@dataclass
class Inventory:
    """Everything the project's SBOM and vulnerability files say."""

    sboms: dict[str, list[Component]] = field(default_factory=dict)  # file name -> components
    statements: list[Statement] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)


def files(root: Path, folder: str) -> list[Path]:
    base = root / folder
    if not base.is_dir():
        return []
    return sorted(p for p in base.glob("*.json") if p.is_file() and not p.is_symlink())


_CACHE: dict[tuple[Any, ...], Inventory] = {}


def inventory(project: Project) -> Inventory:
    """Parsed SBOM and vulnerability files; cached until a file changes (validate runs often)."""
    root = project.root
    paths = files(root, SBOM_DIR) + files(root, VULN_DIR)
    key = (str(root.resolve()), *((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in paths))
    if key not in _CACHE:
        if len(_CACHE) > 8:  # ponytail: tiny cache, cleared wholesale
            _CACHE.clear()
        _CACHE[key] = _inventory(root)
    return _CACHE[key]


def _inventory(root: Path) -> Inventory:
    inv = Inventory()

    def problem(path: Path, exc: Exception) -> None:
        inv.issues.append(Issue(path, "", str(exc), "sbom-invalid"))

    for path in files(root, SBOM_DIR):
        rel = path.relative_to(root).as_posix()
        try:
            inv.sboms[path.name] = read_sbom(path)
            inv.statements += read_statements(path, rel)
        except (SbomError, OSError) as exc:
            problem(path, exc)
    for path in files(root, VULN_DIR):
        try:
            inv.statements += read_statements(path, path.relative_to(root).as_posix())
        except (SbomError, OSError) as exc:
            problem(path, exc)
    return inv


def _merge(states: set[State]) -> State:
    """A manufacturer's fixed/not affected statement (VEX) settles a scanner's finding."""
    order: tuple[State, ...] = ("not_affected", "fixed", "under_investigation")
    for state in order:
        if state in states:
            return state
    return "affected"


def findings(sub: SubModel, inv: Inventory) -> list[Finding]:
    by_purl: dict[str, list[Statement]] = {}
    for s in inv.statements:
        by_purl.setdefault(s.purl, []).append(s)
    threats = [t for t in sub.objects["threats"].values() if isinstance(t, Threat)]
    out: list[Finding] = []
    for element in sub.objects["elements"].values():
        if not isinstance(element, Element):
            continue
        purls = {c.purl for name in element.sbom for c in inv.sboms.get(name, [])}
        grouped: dict[tuple[str, str], list[Statement]] = {}
        for purl in sorted(purls):
            for s in by_purl.get(purl, []):
                grouped.setdefault((s.vuln, purl), []).append(s)
        for (vuln, purl), stmts in sorted(grouped.items()):
            out.append(
                Finding(
                    vuln,
                    element.id,
                    purl,
                    _merge({s.state for s in stmts}),
                    sorted({s.source for s in stmts}),
                    next((s.detail for s in stmts if s.detail), None),
                    sorted(t.id for t in threats if vuln in t.vulnerabilities),
                )
            )
    return out
