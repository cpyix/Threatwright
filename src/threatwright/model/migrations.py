"""Schema migrations: project files from older releases keep working (ADR-0015).

Every project file carries `schema_version`. Loading upgrades an older document
step by step in memory (YAML comments survive); the file changes on the next
save or with `threatwright migrate`. Files from a newer release are refused with
a clear message instead of being misread.

To change the file format:
1. raise SCHEMA_VERSION in objects.py (and the Literal of `schema_version`),
2. add MIGRATIONS[old] that turns a document of version `old` into `old + 1`,
3. keep the compatibility corpus in tests/fixtures/compat loading (see test_compat.py).
"""

from collections.abc import Callable, MutableMapping
from typing import Any

from threatwright.model import objects

Doc = MutableMapping[str, Any]

# MIGRATIONS[n] upgrades a document of schema version n to n + 1, in place.
# `kind` is the model class of the file: ProjectConfig, CustomFields, ModelMeta,
# DiagramLayout, Element, Flow, Asset, Threat, Measure, Question.
MIGRATIONS: dict[int, Callable[[str, Doc], None]] = {}


class NewerSchemaError(ValueError):
    pass


def upgrade(kind: str, doc: Doc) -> bool:
    """Bring `doc` to the current schema version; True if it was older."""
    current = objects.SCHEMA_VERSION
    version = doc.get("schema_version", 1)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError(f"invalid schema_version {version!r}")
    if version > current:
        raise NewerSchemaError(
            f"written by a newer Threatwright (file schema {version}, this release reads up "
            f"to {current}); please update Threatwright"
        )
    for step in range(version, current):
        MIGRATIONS[step](kind, doc)
    if version == current:
        return False
    doc["schema_version"] = current
    return True
