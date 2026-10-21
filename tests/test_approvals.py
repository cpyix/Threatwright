"""Approvals with evidence: who accepted a risk, in which role and when."""

import datetime
from pathlib import Path

from threatwright.model.objects import Decision, Threat
from threatwright.model.store import Project
from threatwright.render import build_documents
from threatwright.rules import validate


def accept(project_dir: Path, decision: Decision, approvers: str = "") -> list[tuple[str, str]]:
    if approvers:
        (project_dir / "method-overrides.yaml").write_text(approvers, encoding="utf-8")
    project = Project.load(project_dir)
    threat = project.models["main"].objects["threats"]["T-0001"]
    assert isinstance(threat, Threat)
    threat.assessment.impact = 1  # low enough to be acceptable
    threat.status = "accepted"
    threat.acceptance = decision
    project.save()
    return [
        (i.code, i.location) for i in validate(Project.load(project_dir)) if i.object_id == "T-0001"
    ]


def test_acceptance_needs_name_role_and_date(project_dir: Path) -> None:
    found = accept(project_dir, Decision(by="Alice", rationale="low risk"))
    assert ("acceptance-undocumented", "acceptance.role") in found
    found = accept(
        project_dir,
        Decision(by="Alice", role="Product Owner", date=datetime.date(2026, 10, 1), rationale="ok"),
    )
    assert "acceptance-undocumented" not in {c for c, _ in found}


def test_approvers_may_be_named_by_role(project_dir: Path) -> None:
    overrides = "acceptance:\n  approvers:\n" + "".join(
        f"    {level}: [Product Owner]\n" for level in range(1, 6)
    )
    by_role = Decision(by="Alice", role="Product Owner", rationale="ok")
    assert "acceptance-not-authorized" not in {
        c for c, _ in accept(project_dir, by_role, overrides)
    }
    nobody = Decision(by="Alice", rationale="ok")
    assert "acceptance-not-authorized" in {c for c, _ in accept(project_dir, nobody, overrides)}


def test_report_lists_approvals_with_git_state(project_dir: Path) -> None:
    accept(
        project_dir,
        Decision(by="Alice", role="Product Owner", date=datetime.date(2026, 10, 1), rationale="ok"),
    )
    (doc,) = build_documents(project_dir, "main", "tr-analysis", "md")
    text = doc.read_text("utf-8")
    approvals = text[text.index("# Freigaben") :]
    assert "kein Git-Repository" in approvals  # the fixture is not in a repository
    assert "T-0001" in approvals and "Product Owner" in approvals and "01.10.2026" in approvals
