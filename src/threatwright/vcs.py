"""Optional Git integration: load a project at a revision, semantic diff, change marks.

Git is never required for normal work. Everything here shells out to the `git`
CLI with argument lists (no shell) and a timeout.
"""

import io
import json
import shutil
import subprocess  # noqa: S404
import tarfile
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from threatwright.method import Method, evaluate
from threatwright.model.objects import COLLECTIONS, ModelObject, Threat
from threatwright.model.store import Project

TIMEOUT = 60
WORKTREE = None  # pass as `rev` to load the working copy


class VcsError(Exception):
    pass


def _git(cwd: Path, *args: str) -> bytes:
    exe = shutil.which("git")
    if exe is None:
        raise VcsError("git is not installed or not on PATH")
    try:
        proc = subprocess.run(  # noqa: S603  (fixed executable, list args, no shell)
            [exe, "-c", "core.quotePath=false", *args],
            cwd=cwd,
            capture_output=True,
            timeout=TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VcsError(f"git {args[0]} failed: {exc}") from exc
    if proc.returncode != 0:
        msg = proc.stderr.decode("utf-8", "replace").strip()
        if "not a git repository" in msg:
            raise VcsError(f"{cwd} is not inside a Git repository")
        raise VcsError(f"git {args[0]}: {msg}")
    return proc.stdout


def _check_rev(rev: str) -> str:
    if not rev or rev.startswith("-") or "\0" in rev:
        raise VcsError(f"invalid revision '{rev}'")
    return rev


def load_project_at(project_root: Path, rev: str | None) -> Project:
    """Load the project as it was at `rev` (None: the working copy).

    The result is a read-only snapshot: its `root` points to a temporary folder
    that no longer exists, so never call `save()` on it.
    """
    if rev is None:
        return Project.load(project_root)
    _git(project_root, "rev-parse", "--verify", "--quiet", f"{_check_rev(rev)}^{{commit}}")
    # ponytail: `git archive` honours export-ignore/export-subst attributes; use
    # ls-tree + cat-file if a project ever relies on those for its YAML files.
    try:  # run in a subfolder, archive limits itself to it and strips the prefix
        data = _git(project_root, "archive", "--format=tar", rev, "--", ".")
    except VcsError as exc:
        if "did not match any files" in str(exc):
            raise VcsError(f"project folder does not exist at {rev}") from exc
        raise
    with tempfile.TemporaryDirectory(prefix="threatwright-") as tmp:
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter="data")
        return Project.load(Path(tmp))


# --- semantic diff ---------------------------------------------------------------

Change = Literal["added", "removed", "changed"]


@dataclass
class ObjectChange:
    collection: str
    id: str
    title: str
    change: Change
    old_id: str | None = None  # set when the id changed (matched by uuid)
    fields: list[str] = field(default_factory=list)
    status: tuple[str | None, str | None] | None = None
    risk: tuple[int | None, int | None] | None = None


@dataclass
class ModelDiff:
    name: str
    change: Change
    meta_fields: list[str] = field(default_factory=list)
    objects: list[ObjectChange] = field(default_factory=list)


@dataclass
class ProjectDiff:
    old_label: str
    new_label: str
    config_fields: list[str] = field(default_factory=list)
    models: list[ModelDiff] = field(default_factory=list)
    risk_labels: dict[int, dict[str, str]] = field(default_factory=dict)

    @property
    def empty(self) -> bool:
        return not self.config_fields and not self.models


def _fields(old: Any, new: Any) -> list[str]:
    a, b = old.model_dump(mode="json"), new.model_dump(mode="json")
    return [k for k in b if a.get(k) != b[k]] + [k for k in a if k not in b]


def _match(
    old: dict[str, ModelObject], new: dict[str, ModelObject]
) -> list[tuple[ModelObject | None, ModelObject | None]]:
    by_uuid = {o.uuid: o for o in old.values()}
    pairs: list[tuple[ModelObject | None, ModelObject | None]] = []
    used: set[str] = set()
    for n in new.values():
        o = by_uuid.get(n.uuid)
        if (
            o is None
            and n.id in old
            and n.id not in used
            and old[n.id].uuid not in {x.uuid for x in new.values()}
        ):
            o = old[n.id]
        if o is not None:
            used.add(o.id)
        pairs.append((o, n))
    pairs += [(o, None) for i, o in old.items() if i not in used]
    return pairs


def _risk(method: Method, project: Project, obj: ModelObject | None) -> int | None:
    if not isinstance(obj, Threat):
        return None
    return evaluate(method, obj, project.config).risk


def semantic_diff(
    old: Project, new: Project, method: Method, old_label: str = "", new_label: str = ""
) -> ProjectDiff:
    diff = ProjectDiff(
        old_label,
        new_label,
        config_fields=_fields(old.config, new.config),
        risk_labels={k: v.model_dump() for k, v in method.risk_levels.levels.items()},
    )
    for name in sorted(old.models.keys() | new.models.keys()):
        o_sub, n_sub = old.models.get(name), new.models.get(name)
        if o_sub is None or n_sub is None:
            md = ModelDiff(name, "added" if o_sub is None else "removed")
        else:
            md = ModelDiff(name, "changed", meta_fields=_fields(o_sub.meta, n_sub.meta))
        for coll in COLLECTIONS:
            o_objs = o_sub.objects[coll] if o_sub else {}
            n_objs = n_sub.objects[coll] if n_sub else {}
            for o, n in _match(o_objs, n_objs):
                cur = n or o
                if cur is None:
                    continue
                change: Change = "added" if o is None else "removed" if n is None else "changed"
                fields = _fields(o, n) if o is not None and n is not None else []
                if change == "changed" and not fields:
                    continue
                oc = ObjectChange(coll, cur.id, cur.title, change, fields=fields)
                if o is not None and n is not None and o.id != n.id:
                    oc.old_id = o.id
                o_status, n_status = getattr(o, "status", None), getattr(n, "status", None)
                if o_status != n_status:
                    oc.status = (o_status, n_status)
                if coll == "threats":
                    oc.risk = (_risk(method, old, o), _risk(method, new, n))
                md.objects.append(oc)
        if md.change != "changed" or md.meta_fields or md.objects:
            diff.models.append(md)
    return diff


_TEXT = {
    "de": {
        "title": "Änderungsnachweis",
        "range": "Vergleich",
        "worktree": "Arbeitskopie",
        "none": "Keine inhaltlichen Änderungen.",
        "project": "Projekteinstellungen geändert",
        "model": "Modell",
        "meta": "Modell-Metadaten geändert",
        "added": "neu",
        "removed": "entfernt",
        "changed": "geändert",
        "renamed": "vorher",
        "status": "Status",
        "risk": "Risiko",
        "newly_rejected": "neu abgelehnt",
        "newly_accepted": "neu akzeptiert",
        "elements": "Elemente",
        "flows": "Datenflüsse",
        "assets": "Assets",
        "threats": "Bedrohungen",
        "measures": "Maßnahmen",
        "questions": "Fragen",
    },
    "en": {
        "title": "Change evidence",
        "range": "Comparison",
        "worktree": "working copy",
        "none": "No content changes.",
        "project": "Project settings changed",
        "model": "Model",
        "meta": "Model metadata changed",
        "added": "added",
        "removed": "removed",
        "changed": "changed",
        "renamed": "formerly",
        "status": "Status",
        "risk": "Risk",
        "newly_rejected": "newly rejected",
        "newly_accepted": "newly accepted",
        "elements": "Elements",
        "flows": "Data flows",
        "assets": "Assets",
        "threats": "Threats",
        "measures": "Measures",
        "questions": "Questions",
    },
}


def _md_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_").replace("\n", " ")


def render_diff(diff: ProjectDiff, fmt: Literal["md", "json"] = "md", lang: str = "de") -> str:
    if fmt == "json":
        return json.dumps(asdict(diff), ensure_ascii=False, indent=2) + "\n"
    t = _TEXT.get(lang, _TEXT["de"])

    def risk(v: int | None) -> str:
        if v is None:
            return "–"
        label = diff.risk_labels.get(v, {}).get(lang)
        return f"{v} ({label})" if label else str(v)

    old, new = diff.old_label or "?", diff.new_label or t["worktree"]
    lines = [f"# {t['title']}", "", f"{t['range']}: `{old}` → `{new}`", ""]
    if diff.empty:
        lines += [t["none"], ""]
    if diff.config_fields:
        lines += [f"{t['project']}: {', '.join(diff.config_fields)}", ""]
    for md in diff.models:
        head = f"## {t['model']} {md.name}"
        lines += [head if md.change == "changed" else f"{head} ({t[md.change]})", ""]
        if md.meta_fields:
            lines += [f"{t['meta']}: {', '.join(md.meta_fields)}", ""]
        for coll in COLLECTIONS:
            items = [oc for oc in md.objects if oc.collection == coll]
            if not items:
                continue
            lines += [f"### {t[coll]}", ""]
            for oc in items:
                parts = [t[oc.change]]
                if oc.old_id:
                    parts.append(f"{t['renamed']} {oc.old_id}")
                if oc.fields:
                    parts[0] += ": " + ", ".join(oc.fields)
                if oc.status:
                    s = f"{t['status']} {oc.status[0] or '–'} → {oc.status[1] or '–'}"
                    if oc.status[1] == "rejected":
                        s += f" (**{t['newly_rejected']}**)"
                    elif oc.status[1] == "accepted":
                        s += f" (**{t['newly_accepted']}**)"
                    parts.append(s)
                if oc.risk and (oc.change != "changed" or oc.risk[0] != oc.risk[1]):
                    parts.append(f"{t['risk']} {risk(oc.risk[0])} → {risk(oc.risk[1])}")
                lines.append(f"- **{oc.id}** {_md_escape(oc.title)}: {'; '.join(parts)}")
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


# --- change marks for the GUI ------------------------------------------------------


def _object_of(path: str) -> tuple[str, str] | None:
    parts = PurePosixPath(path).parts
    if (
        len(parts) == 4
        and parts[0] == "models"
        and parts[2] in COLLECTIONS
        and parts[3].endswith(".yaml")
    ):
        return parts[1], parts[3].removesuffix(".yaml")
    return None


def changed_objects(project_root: Path, since_rev: str | None = None) -> dict[str, set[str]]:
    """Objects whose files differ from `since_rev` (default HEAD), incl. untracked ones.

    Removed objects are included too (their ids no longer exist in the project).
    """
    rev = _check_rev(since_rev) if since_rev else "HEAD"
    names: list[str] = []
    try:
        _git(project_root, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    except VcsError:
        if since_rev is not None:
            raise VcsError(f"unknown revision '{since_rev}'") from None
        # Repository without commits: everything in the project is new.
        names += _git(project_root, "ls-files", "-z", "--cached", "--", ".").decode().split("\0")
    else:
        out = _git(project_root, "diff", "--name-only", "-z", "--relative", rev, "--", ".")
        names += out.decode("utf-8").split("\0")
    untracked = _git(project_root, "ls-files", "-z", "--others", "--exclude-standard", "--", ".")
    names += untracked.decode("utf-8").split("\0")
    result: dict[str, set[str]] = {}
    for name in names:
        hit = _object_of(name)
        if hit:
            result.setdefault(hit[0], set()).add(hit[1])
    return result


@dataclass(frozen=True)
class ReleaseTag:
    name: str
    date: str  # ISO 8601 (tagger date for annotated tags, else commit date)


def release_tags(project_root: Path) -> list[ReleaseTag]:
    """Tags of the repository, newest first ("seit letzter Freigabe")."""
    out = _git(
        project_root,
        "for-each-ref",
        "--sort=-creatordate",
        "--format=%(refname:short)%09%(creatordate:iso-strict)",
        "refs/tags",
    ).decode("utf-8")
    return [ReleaseTag(*line.split("\t", 1)) for line in out.splitlines() if "\t" in line]
