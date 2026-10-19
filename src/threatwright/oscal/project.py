"""Import an OSCAL document into a project and activate it (shared by CLI and GUI)."""

from pathlib import Path
from typing import Literal

from threatwright.model.store import Project
from threatwright.oscal.imports import import_catalog, import_component_definition, import_profile


def import_into_project(
    project_root: Path, file: Path, kind: Literal["catalog", "profile", "component"]
) -> Path:
    """Import and add the resulting library to `libraries:` in threatwright.yaml."""
    if kind == "profile":
        return import_profile(project_root, file)
    importer = import_catalog if kind == "catalog" else import_component_definition
    library = importer(project_root, file)
    project = Project.load(project_root)
    if library.name not in project.config.libraries:
        project.config.libraries = [*project.config.libraries, library.name]
        project.save()
    return library
