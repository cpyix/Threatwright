"""Command line interface. Without a command the GUI starts (from M3 on)."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from threatwright import __version__
from threatwright.branding import PRODUCT_NAME, PROJECT_FILE
from threatwright.model.objects import Configuration, Environment, ModelMeta, ProjectConfig, Zone
from threatwright.model.store import LoadError, Project, SubModel
from threatwright.report import as_json, as_junit, as_sarif, as_text
from threatwright.rules import has_errors, validate

app = typer.Typer(
    name=PRODUCT_NAME.lower(),
    help=f"{PRODUCT_NAME}: threat modelling and risk analysis after BSI TR-03183-1.",
    no_args_is_help=True,
    add_completion=False,
)


class Format(StrEnum):
    text = "text"
    json = "json"
    junit = "junit"
    sarif = "sarif"


class Template(StrEnum):
    empty = "empty"
    tr = "tr"


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[bool, typer.Option("--version", help="Show version and exit.")] = False,
) -> None:
    if version:
        typer.echo(f"{PRODUCT_NAME} {__version__}")
        raise typer.Exit()


@app.command("validate")
def validate_cmd(
    path: Annotated[Path, typer.Argument(help="Project folder.")] = Path("."),
    strict: Annotated[bool, typer.Option(help="Treat warnings as errors.")] = False,
    fmt: Annotated[Format, typer.Option("--format", help="Output format.")] = Format.text,
    output: Annotated[Path | None, typer.Option("-o", "--output", help="Write to file.")] = None,
) -> None:
    """Check schema, references and rules. Exit code 1 on errors."""
    try:
        project = Project.load(path)
    except LoadError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    issues = validate(project)
    root = project.root
    text = {
        Format.text: lambda: as_text(issues, root),
        Format.json: lambda: as_json(issues, root),
        Format.junit: lambda: as_junit(issues, root, strict),
        Format.sarif: lambda: as_sarif(issues, root),
    }[fmt]()
    if output:
        output.write_text(text, encoding="utf-8", newline="\n")
        typer.echo(as_text(issues, root).splitlines()[-1])
    else:
        typer.echo(text, nl=False)
    raise typer.Exit(1 if has_errors(issues, strict) else 0)


OVERRIDES_TEMPLATE = """\
# Project-specific adjustments of the risk method (merged over the method).
# Uncomment and adapt; see docs/methodology.md for every decision point.
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

ZONES = {  # id, de, en, interface default
    "Z-INTERNAL": ("Geräteintern", "Device internal", "physical"),
    "Z-LOCAL": ("Lokale Schnittstellen", "Local interfaces", "local"),
    "Z-PLANT": ("Anlagennetz", "Plant network", "known_network"),
    "Z-EXTERNAL": ("Externes Netz", "External network", "external_network"),
}


@app.command("init")
def init_cmd(
    path: Annotated[Path, typer.Argument(help="Folder for the new project.")] = Path("."),
    template: Annotated[Template, typer.Option(help="empty or tr (TR-03183-1 standard).")] = (
        Template.tr
    ),
    name: Annotated[str | None, typer.Option(help="Project name.")] = None,
    language: Annotated[str, typer.Option(help="de or en.")] = "de",
) -> None:
    """Create a new project."""
    if (path / PROJECT_FILE).exists():
        typer.echo(f"error: {path / PROJECT_FILE} already exists", err=True)
        raise typer.Exit(1)
    if language not in ("de", "en"):
        raise typer.BadParameter("language must be de or en")
    path.mkdir(parents=True, exist_ok=True)
    config = ProjectConfig(name=name or path.resolve().name, language=language)
    project = Project(root=path, config=config)
    if template is Template.tr:
        de = language == "de"
        meta = ModelMeta(
            title="Hauptmodell" if de else "Main model",
            configurations=[Configuration(id="K-A", title="Standard" if de else "Standard")],
            zones=[
                Zone(id=zid, title=t_de if de else t_en, environment=Environment(interface=iface))
                for zid, (t_de, t_en, iface) in ZONES.items()
            ],
        )
        project.models["main"] = SubModel("main", meta)
        (path / "method-overrides.yaml").write_text(
            OVERRIDES_TEMPLATE, encoding="utf-8", newline="\n"
        )
    project.save()
    gitignore = path / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("build/\n", encoding="utf-8", newline="\n")
    typer.echo(f"created {PRODUCT_NAME} project in {path}")
