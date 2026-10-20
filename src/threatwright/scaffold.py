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


# Product types = bundled libraries: id: (de, en); the order is the display order.
PRODUCT_LIBRARIES: dict[str, tuple[str, str]] = {
    "ot": ("Maschine oder Anlage", "Machine or plant"),
    "iot": ("Vernetztes Gerät, IoT, Consumer", "Connected device, IoT, consumer"),
    "software": ("Software", "Software"),
}

# Without "ot" there is no plant network: the third zone is the local network.
LAN_ZONE = ("Lokales Netz (LAN/WLAN)", "Local network (LAN/WLAN)", "known_network")


class ProjectExists(Exception):
    pass


def create_project(
    path: Path,
    template: Literal["empty", "tr"] = "tr",
    name: str | None = None,
    language: Literal["de", "en"] = "de",
    libraries: list[str] | None = None,
) -> Project:
    libs = ["ot"] if libraries is None else libraries
    unknown = [lib for lib in libs if lib not in PRODUCT_LIBRARIES]
    if not libs or unknown:
        raise ValueError(
            f"libraries must be a non-empty list of {', '.join(PRODUCT_LIBRARIES)}"
            + (f" (unknown: {', '.join(unknown)})" if unknown else "")
        )
    libs = [lib for lib in PRODUCT_LIBRARIES if lib in libs]
    if (path / PROJECT_FILE).exists():
        raise ProjectExists(f"{path / PROJECT_FILE} already exists")
    path.mkdir(parents=True, exist_ok=True)
    config = ProjectConfig(name=name or path.resolve().name, language=language, libraries=libs)
    project = Project(root=path, config=config)
    if template == "tr":
        de = language == "de"
        zones = ZONES
        if "ot" not in libs:
            zones = {
                ("Z-LAN" if k == "Z-PLANT" else k): LAN_ZONE if k == "Z-PLANT" else v
                for k, v in ZONES.items()
            }
        project.models["main"] = SubModel(
            "main",
            ModelMeta(
                title="Hauptmodell" if de else "Main model",
                configurations=[Configuration(id="K-A", title="Standard")],
                zones=[
                    Zone(id=zid, title=t_de if de else t_en, environment=Environment(interface=i))
                    for zid, (t_de, t_en, i) in zones.items()
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
