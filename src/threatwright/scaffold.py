"""Create new projects (shared by `threatwright init` and the GUI)."""

from pathlib import Path
from typing import Literal

from threatwright.branding import PROJECT_FILE
from threatwright.model.objects import Configuration, Environment, ModelMeta, ProjectConfig, Zone
from threatwright.model.store import Project, SubModel

OVERRIDES_TEMPLATE = """\
# Project-specific adjustments of the risk method (merged over the method).
# Uncomment and adapt; see docs/methodik.md for every decision point.
#
# risk_matrix:
#   matrix_row_from_exposure: inverted   # or: literal
# acceptance:
#   max_acceptable_risk: 2               # 1 very low .. 5 very high
#   approvers:
#     2: [Product Owner]
#   rules:                               # lists replace the method's list
#     - id: safety-stricter
#       label: {de: Strengere Grenze bei Sicherheitsbezug, en: Stricter limit for safety}
#       enabled: true
#       when: {threat.safety_related: true}
#       max_acceptable_risk: 1
"""

ZONES = {  # id: (de, en, interface default)
    "Z-INTERNAL": ("Geräteintern", "Device internal", "physical"),
    "Z-LOCAL": ("Lokale Schnittstellen", "Local interfaces", "local"),
    "Z-PLANT": ("Anlagennetz", "Plant network", "known_network"),
    "Z-EXTERNAL": ("Externes Netz", "External network", "external_network"),
}


class ProjectExists(Exception):
    pass


def create_project(
    path: Path,
    template: Literal["empty", "tr"] = "tr",
    name: str | None = None,
    language: Literal["de", "en"] = "de",
) -> Project:
    if (path / PROJECT_FILE).exists():
        raise ProjectExists(f"{path / PROJECT_FILE} already exists")
    path.mkdir(parents=True, exist_ok=True)
    config = ProjectConfig(name=name or path.resolve().name, language=language, libraries=["ot"])
    project = Project(root=path, config=config)
    if template == "tr":
        de = language == "de"
        project.models["main"] = SubModel(
            "main",
            ModelMeta(
                title="Hauptmodell" if de else "Main model",
                configurations=[Configuration(id="K-A", title="Standard")],
                zones=[
                    Zone(id=zid, title=t_de if de else t_en, environment=Environment(interface=i))
                    for zid, (t_de, t_en, i) in ZONES.items()
                ],
            ),
        )
        (path / "method-overrides.yaml").write_text(
            OVERRIDES_TEMPLATE, encoding="utf-8", newline="\n"
        )
    project.save()
    gitignore = path / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("build/\n", encoding="utf-8", newline="\n")
    return project
