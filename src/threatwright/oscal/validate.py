"""Read and validate OSCAL JSON documents against the bundled NIST schemas (ADR-0012).

Schemas are never fetched: every `$ref` must resolve inside the bundled file,
remote retrieval raises. Only JSON is supported.
"""

import json
import re
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT7

from threatwright.model.store import Issue

OSCAL_VERSION = "1.2.3"
SCHEMA_DIR = Path(__file__).parent / "schemas" / OSCAL_VERSION
MAX_BYTES = 50 * 1024 * 1024
MAX_ISSUES = 100
SUPPORTED = {
    "catalog": "oscal_catalog_schema.json",
    "profile": "oscal_profile_schema.json",
    "component-definition": "oscal_component_schema.json",
}
# Root keys of the other OSCAL models; validated with the complete schema.
OTHER_MODELS = {
    "system-security-plan",
    "assessment-plan",
    "assessment-results",
    "plan-of-action-and-milestones",
    "mapping-collection",
}
COMPLETE = "oscal_complete_schema.json"

# The NIST schemas use the Unicode classes \p{L} and \p{N} (token datatype),
# which Python's re does not know. [^\W\d_] is "letter" and \d covers Unicode
# decimal digits; \p{N} also includes other numerics (e.g. Roman numerals),
# a negligible gap for identifier tokens (ADR-0012).
_UNICODE_CLASSES = {r"\p{L}": r"[^\W\d_]", r"\p{N}": r"\d"}


class OscalError(Exception):
    def __init__(self, issues: list[Issue]) -> None:
        super().__init__("; ".join(str(i) for i in issues))
        self.issues = issues


@cache
def _regex(pattern: str) -> re.Pattern[str]:
    for src, dst in _UNICODE_CLASSES.items():
        pattern = pattern.replace(src, dst)
    return re.compile(pattern)


def _pattern(validator: Any, pattern: str, instance: Any, schema: dict[str, Any]) -> Iterator[Any]:
    if validator.is_type(instance, "string") and not _regex(pattern).search(instance):
        yield jsonschema.ValidationError(f"{instance!r} does not match {pattern!r}")


def _no_retrieve(uri: str) -> Resource[Any]:
    raise NoSuchResource(ref=uri)  # type: ignore[call-arg]


_Validator = jsonschema.validators.extend(jsonschema.Draft7Validator, {"pattern": _pattern})


@cache
def _validator(schema_file: str) -> Any:
    schema = json.loads((SCHEMA_DIR / schema_file).read_text(encoding="utf-8"))
    registry: Registry[Any] = Registry(retrieve=_no_retrieve).with_resource(  # type: ignore[call-arg]
        schema["$id"], DRAFT7.create_resource(schema)
    )
    return _Validator(
        schema, registry=registry, format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER
    )


def _location(path: Any) -> str:
    return ".".join(str(p) for p in path)


def load_document(path: Path) -> tuple[str | None, dict[str, Any], list[Issue]]:
    """Parse and validate; returns (model, document, issues)."""
    path = Path(path)

    def error(msg: str, code: str = "oscal-format", loc: str = "") -> Issue:
        return Issue(path, loc, msg, code)

    if not path.is_file():
        return None, {}, [error("file not found")]
    if path.suffix.lower() in {".xml", ".yaml", ".yml"}:
        fmt = path.suffix.lstrip(".").upper()
        return None, {}, [error(f"OSCAL {fmt} is not supported; convert the file to OSCAL JSON")]
    if path.stat().st_size > MAX_BYTES:
        return None, {}, [error(f"file larger than {MAX_BYTES} bytes", "oscal-too-large")]
    raw = path.read_bytes()
    try:
        doc = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        hint = " (XML or YAML is not supported)" if raw.lstrip()[:1] in (b"<", b"-") else ""
        return None, {}, [error(f"invalid JSON: {exc}{hint}")]
    if not isinstance(doc, dict):
        return None, {}, [error("top level must be a JSON object")]
    roots = [k for k in doc if k != "$schema"]
    if len(roots) != 1:
        return None, doc, [error(f"expected exactly one OSCAL model key, found {roots}")]
    model = roots[0]
    issues: list[Issue] = []
    if model in SUPPORTED:
        schema = SUPPORTED[model]
    elif model in OTHER_MODELS:
        issues.append(
            error(
                f"unsupported model '{model}': only catalog, profile and component-definition "
                "can be imported",
                "oscal-unsupported",
            )
        )
        schema = COMPLETE
    else:
        return model, doc, [error(f"unknown OSCAL model '{model}'", "oscal-unsupported")]
    errors = sorted(_validator(schema).iter_errors(doc), key=lambda e: list(map(str, e.path)))
    for err in errors[:MAX_ISSUES]:
        # anyOf/oneOf failures report the whole instance; the deepest sub-error is useful.
        leaf = jsonschema.exceptions.best_match([err])
        msg = leaf.message if len(leaf.message) <= 300 else leaf.message[:297] + "..."
        issues.append(error(msg, "oscal-schema", _location(leaf.absolute_path)))
    if len(errors) > MAX_ISSUES:
        issues.append(error(f"{len(errors) - MAX_ISSUES} more schema errors", "oscal-schema"))
    return model, doc, issues


def validate_oscal(path: Path) -> list[Issue]:
    return load_document(path)[2]


def load_valid(path: Path, expected: str) -> dict[str, Any]:
    """Document body of the expected model; raises OscalError on any problem."""
    model, doc, issues = load_document(path)
    if not issues and model != expected:
        issues = [Issue(Path(path), "", f"expected a {expected}, found {model}", "oscal-format")]
    if issues:
        raise OscalError(issues)
    body: dict[str, Any] = doc[expected]
    return body
