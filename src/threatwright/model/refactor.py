"""Rename an object ID and update every reference in its model (brief §5.1)."""

import re

from threatwright.model.objects import COLLECTIONS, ModelObject, NodeLayout
from threatwright.model.store import Project

ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*-[0-9]{4,}$")


def _replace(value: object, old: str, new: str, word: re.Pattern[str]) -> object:
    if isinstance(value, str):
        return new if value == old else word.sub(new, value)
    if isinstance(value, list):
        return [_replace(v, old, new, word) for v in value]
    if isinstance(value, dict):
        return {k: _replace(v, old, new, word) for k, v in value.items()}
    return value


def rename_id(project: Project, model: str, collection: str, old: str, new: str) -> int:
    """Rename `old` to `new`; returns the number of other objects that were updated.

    References in lists, scalar fields and free text (whole-word matches) are
    rewritten. The uuid stays the same, so exchange formats keep matching.
    """
    sub = project.models[model]
    objects = sub.objects[collection]
    if old not in objects:
        raise KeyError(old)
    if not ID_PATTERN.match(new):
        raise ValueError(f"invalid id '{new}'")
    if any(new in objs for objs in sub.objects.values()):
        raise ValueError(f"id '{new}' already exists")

    word = re.compile(rf"(?<![\w-]){re.escape(old)}(?![\w-])")
    changed = 0
    for coll, objs in sub.objects.items():
        for oid, obj in list(objs.items()):
            data = obj.model_dump(mode="json")
            updated = _replace(data, old, new, word)
            if oid == old:
                updated["id"] = new  # type: ignore[index]
            if updated != data:
                if oid != old:
                    changed += 1
                objs[oid] = COLLECTIONS[coll].model_validate(updated)
    renamed: ModelObject = objects.pop(old)
    objects[new] = renamed
    if old in sub.layout.nodes:
        node = sub.layout.nodes.pop(old)
        sub.layout.nodes[new] = NodeLayout.model_validate(node.model_dump())
    project.move_document(model, collection, old, new)
    return changed
