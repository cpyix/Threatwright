"""JSON Schemas for every file type, generated from the Pydantic models.

The committed files under schemas/ are checked against this in the tests,
so editors and external tools always see the current schema.
"""

import json
import sys
from pathlib import Path

from threatwright.model.objects import FILE_TYPES, SCHEMA_VERSION


def render_schemas() -> dict[str, str]:
    out = {}
    for name, cls in FILE_TYPES.items():
        schema = cls.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"{name}.v{SCHEMA_VERSION}.schema.json"
        out[schema["$id"]] = json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    return out


def write_schemas(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for filename, text in render_schemas().items():
        (target / filename).write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    write_schemas(Path(sys.argv[1] if len(sys.argv) > 1 else "schemas"))
