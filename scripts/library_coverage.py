"""Report library integrity and STRIDE coverage per element type.

usage: python scripts/library_coverage.py [library ...] [--only id,id,...]
Exit code 1 if the library is invalid or an element type lacks a threat for a
STRIDE category that is relevant for its kind (method stride_per_kind).
"""

import sys
from pathlib import Path

from threatwright.library import load_libraries
from threatwright.method import load_method
from threatwright.model.objects import ProjectConfig


def main(argv: list[str]) -> int:
    only = None
    if "--only" in argv:
        i = argv.index("--only")
        only = set(argv[i + 1].split(","))
        argv = argv[:i] + argv[i + 2 :]
    libs = load_libraries(argv or ["ot"])
    method = load_method(Path("."), ProjectConfig(name="coverage"))
    for issue in libs.issues:
        print(issue)
    missing = 0
    for el in libs.elements.values():
        if only and el.id not in only:
            continue
        have = {s for t in libs.threats.values() if el.id in t.applies_to for s in t.stride}
        need = method.stride_per_kind.map[el.kind]
        gaps = [s for s in need if s not in have]
        if gaps:
            missing += 1
            print(f"{el.id} ({el.kind}): missing {' '.join(gaps)}")
    print(
        f"{len(libs.elements)} elements, {len(libs.threats)} threats, "
        f"{len(libs.measures)} measures, {missing} element types with gaps"
    )
    return 1 if libs.issues or missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
