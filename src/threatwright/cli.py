"""Command line interface. Without a command the GUI starts (from M3 on)."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from threatwright import __version__
from threatwright.branding import PRODUCT_NAME, PROJECT_FILE
from threatwright.ci import render_ci
from threatwright.interop import (
    ImportFailed,
    export_threats,
    import_csv,
    import_threat_dragon,
)
from threatwright.library import check_library_refs, load_libraries
from threatwright.method import Method, MethodError, load_method
from threatwright.model.objects import SCHEMA_VERSION
from threatwright.model.store import LoadError, Project
from threatwright.oscal import OSCAL_VERSION, OscalError, validate_oscal
from threatwright.oscal.project import import_into_project
from threatwright.render import (
    OUT_FORMATS,
    RenderError,
    build_documents,
    check_template,
    derive_template,
)
from threatwright.report import as_json, as_junit, as_sarif, as_text
from threatwright.rules import has_errors, validate
from threatwright.scaffold import ProjectExists, create_project
from threatwright.vcs import VcsError, load_project_at, render_diff, semantic_diff

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


class DiffFormat(StrEnum):
    md = "md"
    json = "json"


class ExportFormat(StrEnum):
    csv = "csv"
    json = "json"
    xlsx = "xlsx"


class ImportSource(StrEnum):
    threat_dragon = "threat-dragon"
    csv = "csv"


def _method_or_exit(project: Project) -> Method:
    try:
        return load_method(project.root, project.config)
    except MethodError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc


@app.command("diff")
def diff_cmd(
    rev1: Annotated[str, typer.Argument(help="Older revision (tag, branch, commit).")],
    rev2: Annotated[
        str | None, typer.Argument(help="Newer revision; default: working copy.")
    ] = None,
    path: Annotated[Path, typer.Option("--path", help="Project folder.")] = Path("."),
    fmt: Annotated[DiffFormat, typer.Option("--format")] = DiffFormat.md,
    output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
) -> None:
    """Semantic change evidence between two Git revisions."""
    project = _load(path)
    method = _method_or_exit(project)
    try:
        old = load_project_at(path, rev1)
        new = load_project_at(path, rev2) if rev2 else project
    except VcsError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    diff = semantic_diff(old, new, method, rev1, rev2 or "working copy")
    text = render_diff(diff, fmt.value, project.config.language)
    if output:
        output.write_text(text, encoding="utf-8", newline="\n")
    else:
        typer.echo(text, nl=False)


@app.command("export")
def export_cmd(
    path: Annotated[Path, typer.Argument(help="Project folder.")] = Path("."),
    fmt: Annotated[ExportFormat, typer.Option("--format")] = ExportFormat.csv,
    output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
) -> None:
    """Threat and measure lists for other tools."""
    project = _load(path)
    out = output or project.root / "build" / f"threats.{fmt.value}"
    out.parent.mkdir(parents=True, exist_ok=True)
    for written in export_threats(project, _method_or_exit(project), fmt.value, out):
        typer.echo(f"wrote {written}")


@app.command("import")
def import_cmd(
    file: Annotated[Path, typer.Argument(help="File to import.")],
    source: Annotated[ImportSource, typer.Option("--from", help="Source format.")],
    model: Annotated[str, typer.Option(help="Target model (created if missing).")],
    path: Annotated[Path, typer.Option("--path", help="Project folder.")] = Path("."),
) -> None:
    """Import from Threat Dragon (v2 JSON) or CSV. Only adds objects."""
    importer = import_threat_dragon if source is ImportSource.threat_dragon else import_csv
    try:
        result = importer(path, file, model)
    except ImportFailed as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    counts = ", ".join(f"{k}: {v}" for k, v in result.counts.items())
    typer.echo(f"imported into model '{result.model}': {counts}")
    for warning in result.warnings:
        typer.echo(f"warning: {warning}")


oscal_app = typer.Typer(
    help="OSCAL import and validation (import only, ADR-0006).", no_args_is_help=True
)
app.add_typer(oscal_app, name="oscal")


class OscalKind(StrEnum):
    catalog = "catalog"
    profile = "profile"
    component = "component"


@oscal_app.command("validate")
def oscal_validate_cmd(file: Annotated[Path, typer.Argument(help="OSCAL JSON file.")]) -> None:
    """Validate an OSCAL document against the bundled NIST schemas."""
    issues = validate_oscal(file)
    for issue in issues:
        typer.echo(str(issue))
    typer.echo(f"OSCAL {OSCAL_VERSION}: {len(issues)} issue(s)")
    raise typer.Exit(1 if any(i.severity == "error" for i in issues) else 0)


@oscal_app.command("import")
def oscal_import_cmd(
    file: Annotated[Path, typer.Argument(help="OSCAL JSON file.")],
    kind: Annotated[OscalKind, typer.Option("--as", help="Document type.")],
    path: Annotated[Path, typer.Option("--path", help="Project folder.")] = Path("."),
) -> None:
    """Import an OSCAL catalog, profile or component definition into the project."""
    _load(path)
    try:
        written = import_into_project(path, file, kind.value)
    except OscalError as exc:
        for issue in exc.issues:
            typer.echo(str(issue), err=True)
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"imported into {written}")


template_app = typer.Typer(help="Document templates.", no_args_is_help=True)
app.add_typer(template_app, name="template")


@app.command("build")
def build_cmd(
    path: Annotated[Path, typer.Argument(help="Project folder.")] = Path("."),
    model: Annotated[str | None, typer.Option(help="Only this model.")] = None,
    template: Annotated[str | None, typer.Option(help="Only this template.")] = None,
    fmt: Annotated[
        list[str] | None, typer.Option("--format", help="docx, odt, md, html, pdf; repeatable.")
    ] = None,
    output: Annotated[Path | None, typer.Option("-o", "--output", help="Output folder.")] = None,
) -> None:
    """Generate documents from templates (default output: <project>/build)."""
    _load(path)
    formats: list[str | None] = list(fmt) if fmt else [None]
    unknown = [f for f in formats if f is not None and f not in OUT_FORMATS]
    if unknown:
        raise typer.BadParameter(f"unknown format(s): {', '.join(unknown)}")
    try:
        for f in formats:
            for written in build_documents(path, model, template, f, output):  # type: ignore[arg-type]
                typer.echo(f"wrote {written}")
    except (RenderError, MethodError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc


@template_app.command("check")
def template_check_cmd(
    path: Annotated[Path, typer.Argument(help="Template package folder or template.yaml.")],
) -> None:
    """Report syntax errors and unknown variables in a template."""
    issues = check_template(path)
    for issue in issues:
        typer.echo(str(issue))
    typer.echo(f"{len(issues)} issue(s)")
    raise typer.Exit(1 if any(i.severity == "error" for i in issues) else 0)


@template_app.command("derive")
def template_derive_cmd(
    document: Annotated[Path, typer.Argument(help="Existing .docx or .odt of your company.")],
    out_dir: Annotated[Path, typer.Argument(help="New template folder (its name becomes the id).")],
) -> None:
    """Turn an existing document into a template (keeps styles, header and footer)."""
    try:
        written = derive_template(document, out_dir)
    except RenderError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"created {written}; check it with: threatwright template check {out_dir}")


@app.command("migrate")
def migrate_cmd(path: Annotated[Path, typer.Argument(help="Project folder.")] = Path(".")) -> None:
    """Bring all project files to the current schema version."""
    project = _load(path)
    outdated = [i for i in project.issues if i.location == "schema_version"]
    for issue in outdated:
        typer.echo(str(issue), err=True)
    if outdated:
        # ponytail: no older schema exists yet; add a migration step per version here
        typer.echo("error: unknown schema_version; this release only knows version 1", err=True)
        raise typer.Exit(1)
    typer.echo(f"all files at schema version {SCHEMA_VERSION}; nothing to migrate")


class CiKind(StrEnum):
    gitlab = "gitlab"
    github = "github"


@app.command("ci")
def ci_cmd(
    kind: Annotated[CiKind, typer.Argument(help="gitlab or github.")] = CiKind.gitlab,
    path: Annotated[Path, typer.Argument(help="Project folder.")] = Path("."),
    image: Annotated[str | None, typer.Option(help="Container image to use.")] = None,
) -> None:
    """Print a pipeline template pre-filled for this project."""
    try:
        typer.echo(render_ci(path, kind.value, image), nl=False)
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc


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
