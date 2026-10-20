"""Projects written by every earlier release keep working (ADR-0015).

tests/fixtures/compat/v<version>/ holds a sample project per release, added by
scripts/compat_snapshot.py when the release is cut. Each must load without
issues, keep its references intact, survive a save and still render documents.
"""

import shutil
from pathlib import Path

import pytest

from threatwright import history
from threatwright.model.store import Project
from threatwright.render import build_documents
from threatwright.rules import validate

COMPAT = Path(__file__).parent / "fixtures" / "compat"
# Errors that mean the format or a reference broke, as opposed to modelling findings.
STRUCTURAL = {
    "schema",
    "method-invalid",
    "library-invalid",
    "library-ref-unknown",
    "unresolved-ref",
    "unresolved-text-ref",
    "unknown-configuration",
    "unknown-zone",
    "unknown-asset-class",
    "unknown-indicator-value",
    "custom-unknown",
}
RELEASES = sorted(COMPAT.iterdir())


def test_corpus_exists() -> None:
    assert RELEASES, "add the first sample with scripts/compat_snapshot.py"


@pytest.mark.parametrize("release", RELEASES, ids=lambda p: p.name)
def test_project_of_earlier_release_still_works(release: Path, tmp_path: Path) -> None:
    root = tmp_path / release.name
    shutil.copytree(release, root)

    project = Project.load(root)
    assert project.issues == []
    structural = [i for i in validate(project) if i.code in STRUCTURAL]
    assert structural == []
    before = history.dump(project.models)

    project.save()  # what `threatwright migrate` or a save in the GUI does
    reloaded = Project.load(root)
    assert reloaded.issues == [] and reloaded.migrated == []
    assert history.dump(reloaded.models) == before

    written = build_documents(root, None, None, "md")
    assert written and all(p.stat().st_size > 0 for p in written)
