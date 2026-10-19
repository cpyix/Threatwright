"""Command line interface. Without a command the GUI starts (from M3 on)."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from threatwright import __version__
from threatwright.branding import PRODUCT_NAME, PROJECT_FILE
from threatwright.library import check_library_refs, load_libraries
from threatwright.model.store import LoadError, Project
from threatwright.report import as_json, as_junit, as_sarif, as_text
from threatwright.rules import has_errors, validate
from threatwright.scaffold import ProjectExists, create_project

app = typer.Typer(
    name=PRODUCT_NAME.lower(),
    help=f"{PRODUCT_NAME}: threat modelling and risk analysis after BSI TR-03183-1.",
    add_completion=False,
)
library_app = typer.Typer(help="Element, threat and measure libraries.", no_args_is_help=True)
app.add_typer(library_app, name="library")


def _load(path: Path) -> Project:
    try:
        return Project.load(path)
    except LoadError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc


class Format(StrEnum):
    text = "text"
    json = "json"
    junit = "junit"
    sarif = "sarif"


class Template(StrEnum):
    empty = "empty"
    tr = "tr"


class Language(StrEnum):
    de = "de"
    en = "en"


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", help="Show version and exit.")] = False,
    project: Annotated[
        Path | None, typer.Option(help="Project to open in the GUI (default: current folder).")
    ] = None,
    browser: Annotated[bool, typer.Option(help="Open the default browser.")] = True,
) -> None:
    """Without a command: start the GUI on a local port."""
    if version:
        typer.echo(f"{PRODUCT_NAME} {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        from threatwright.server import serve

        if project is None and (Path(".") / PROJECT_FILE).exists():
            project = Path(".")
        serve(project, open_browser=browser)


@app.command("validate")
def validate_cmd(
    path: Annotated[Path, typer.Argument(help="Project folder.")] = Path("."),
    strict: Annotated[bool, typer.Option(help="Treat warnings as errors.")] = False,
    fmt: Annotated[Format, typer.Option("--format", help="Output format.")] = Format.text,
    output: Annotated[Path | None, typer.Option("-o", "--output", help="Write to file.")] = None,
) -> None:
    """Check schema, references and rules. Exit code 1 on errors."""
    project = _load(path)
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


@app.command("init")
def init_cmd(
    path: Annotated[Path, typer.Argument(help="Folder for the new project.")] = Path("."),
    template: Annotated[Template, typer.Option(help="empty or tr (TR-03183-1 standard).")] = (
        Template.tr
    ),
    name: Annotated[str | None, typer.Option(help="Project name.")] = None,
    language: Annotated[Language, typer.Option(help="Project language.")] = Language.de,
) -> None:
    """Create a new project."""
    try:
        create_project(path, template.value, name, language.value)
    except ProjectExists as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"created {PRODUCT_NAME} project in {path}")


@library_app.command("update")
def library_update_cmd(
    path: Annotated[Path, typer.Argument(help="Project folder.")] = Path("."),
) -> None:
    """Show model objects whose library entry has a newer revision."""
    project = _load(path)
    libs = load_libraries(project.config.libraries, project.root)
    for issue in libs.issues:
        typer.echo(str(issue), err=True)
    _, outdated = check_library_refs(project, libs)
    for o in outdated:
        typer.echo(f"{o.model}/{o.object_id} {o.title}: {o.ref} -> rev {o.current_rev}")
    typer.echo(f"{len(outdated)} object(s) with newer library revisions")
