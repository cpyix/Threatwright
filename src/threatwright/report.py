"""Render validation issues for humans and CI systems."""

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from threatwright import __version__
from threatwright.branding import PRODUCT_NAME
from threatwright.model.store import Issue
from threatwright.rules import relative


def as_text(issues: list[Issue], root: Path) -> str:
    lines = [
        f"{i.severity}: {relative(i, root)}{f' [{i.location}]' if i.location else ''}: "
        f"{i.message} ({i.code})"
        for i in issues
    ]
    errors = sum(i.severity == "error" for i in issues)
    lines.append(f"{errors} error(s), {len(issues) - errors} warning(s)")
    return "\n".join(lines) + "\n"


def as_json(issues: list[Issue], root: Path) -> str:
    rows = [
        {
            "severity": i.severity,
            "code": i.code,
            "file": relative(i, root),
            "location": i.location,
            "model": i.model,
            "object": i.object_id,
            "message": i.message,
        }
        for i in issues
    ]
    return json.dumps(rows, indent=2, ensure_ascii=False) + "\n"


def as_junit(issues: list[Issue], root: Path, strict: bool = False) -> str:
    """One test case per issue; GitLab shows them in the merge request widget."""
    failing = [i for i in issues if strict or i.severity == "error"]
    suites = ET.Element("testsuites")
    suite = ET.SubElement(
        suites,
        "testsuite",
        name=f"{PRODUCT_NAME} validate",
        tests=str(max(len(issues), 1)),
        failures=str(len(failing)),
    )
    if not issues:
        ET.SubElement(suite, "testcase", classname="validate", name="project is valid")
    for i in issues:
        case = ET.SubElement(
            suite,
            "testcase",
            classname=relative(i, root) or "project",
            name=f"{i.code} {i.location}",
        )
        if i in failing:
            ET.SubElement(case, "failure", message=i.message).text = f"{i.severity}: {i.message}"
        else:
            ET.SubElement(case, "system-out").text = f"{i.severity}: {i.message}"
    return ET.tostring(suites, encoding="unicode") + "\n"


def as_sarif(issues: list[Issue], root: Path) -> str:
    codes = sorted({i.code for i in issues})
    run = {
        "tool": {
            "driver": {
                "name": PRODUCT_NAME,
                "version": __version__,
                "rules": [{"id": c} for c in codes],
            }
        },
        "results": [
            {
                "ruleId": i.code,
                "level": i.severity,
                "message": {"text": f"{i.location}: {i.message}" if i.location else i.message},
                "locations": [
                    {"physicalLocation": {"artifactLocation": {"uri": relative(i, root)}}}
                ]
                if i.path
                else [],
            }
            for i in issues
        ],
    }
    doc = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [run],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
