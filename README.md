# Threatwright

Local-first threat modelling and risk analysis for products with digital elements under the EU Cyber Resilience Act (CRA), following **BSI TR-03183-1**. Built for machine and plant manufacturers (OT) whose engineers are not security specialists. Status: **pre-alpha**.

- **Offline and local:** Windows and Linux, no admin rights, no network access at runtime, no telemetry.
- **Git is the database:** one YAML file per object, stable IDs, saving without changes produces no diff. Merge requests are the change history; `threatwright diff` creates change evidence between releases.
- **TR-03183-1 as configuration:** scales, factors, risk matrix and acceptance rules live in a method file with page references and can be overridden per project ([Methodik](docs/methodik.md)).
- **Building blocks instead of empty forms:** OT library with 42 element types, 131 threat and 96 measure templates; STRIDE assistant, coverage matrix, data flow diagram.
- **Documents from your own templates:** DOCX, ODT, Markdown, HTML, PDF via LibreOffice; layout and outline without code changes ([Vorlagenreferenz](docs/vorlagenreferenz.md)).
- **CI:** the same checks as the GUI in GitLab or GitHub pipelines, template pre-filled per project ([CI](docs/ci.md)).
- **Interop:** OSCAL import (catalogs such as Grundschutz++, profiles, component definitions), Threat Dragon and CSV import, CSV/JSON/XLSX export.

## Documentation (German)

[Schnellstart](docs/schnellstart.md) · [Tutorial](docs/tutorial.md) · [Methodik](docs/methodik.md) · [Prüfregeln](docs/pruefregeln.md) · [Ist das ein Cyberrisiko?](docs/faq-cyberrisiko.md) · [Bibliotheksformat](docs/bibliotheksformat.md) · [Vorlagenreferenz](docs/vorlagenreferenz.md) · [Git-Arbeitsweise](docs/git-arbeitsweise.md) · [OSCAL](docs/oscal.md) · [CI](docs/ci.md) · [Offene Prüfpunkte](docs/VERIFY.md) · [CRA-Selbstbewertung](docs/cra-self-assessment.md)

Architecture decisions (English): [`docs/adr/`](docs/adr/).

## Install and run

### Option 1: portable download (no Python, no admin rights)

From the [releases](https://github.com/cpyix/threatwright/releases) download `threatwright-<version>-windows-amd64.zip` or `threatwright-<version>-linux-x86_64.tar.gz`, unpack it anywhere (e.g. your user folder or a USB stick) and run `threatwright.exe` (Windows) or `./threatwright` (Linux). Without arguments the GUI opens in your default browser. Verify downloads with `SHA256SUMS` (see [SECURITY.md](SECURITY.md)).

### Option 2: with Python (3.12+)

```
pipx install threatwright
threatwright
```

### Option 3: from source

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 24 (only to build the GUI bundle). Optional: Git (change evidence), LibreOffice (PDF output).

```
git clone https://github.com/cpyix/threatwright.git
cd threatwright
uv sync
cd app && npm ci && npm run build && cd ..    # builds the GUI into src/threatwright/web
uv run threatwright                           # start the GUI
```

Build the portable bundle yourself: `uv run python packaging/build.py` (output in `dist/`).

## Usage

```
threatwright init my-product --name "My product"   # new project (TR-03183-1 standard)
threatwright --project my-product                  # GUI in the default browser
threatwright --project my-product --no-browser     # GUI, prints the URL instead
threatwright validate my-product                   # all rules; exit code 1 on errors
threatwright build my-product --format docx        # documents into my-product/build
threatwright diff v1.0 --path my-product           # change evidence since tag v1.0
threatwright ci gitlab my-product                  # GitLab pipeline for this project
threatwright --help                                # all commands
```

Started inside a project folder, `threatwright` opens that project directly. The GUI runs on `127.0.0.1` only, on a random port, protected by a per-start token and a strict Content Security Policy; nothing leaves your machine.

## Docker (CLI and CI)

The image contains the CLI, Git and LibreOffice (for PDF). It is meant for pipelines and batch use, not for the GUI: the GUI binds to `127.0.0.1` inside the container by design and is therefore not reachable from the host. Run the GUI locally instead.

Build the image locally from the repository root (the frontend is built inside the image, no local Node.js needed):

```
docker build -t threatwright:local .
```

Run it on a project in the current folder:

```
# Linux / macOS
docker run --rm -v "$PWD:/work" --user "$(id -u):$(id -g)" threatwright:local validate .
docker run --rm -v "$PWD:/work" --user "$(id -u):$(id -g)" threatwright:local build . --format pdf

# Windows PowerShell
docker run --rm -v "${PWD}:/work" threatwright:local validate .
```

`--user` makes generated files belong to you instead of the container user. Released images are published as `ghcr.io/cpyix/threatwright:<version>`; the pipeline templates use them.

## Development

```
uv run pytest                                # incl. GUI end-to-end and accessibility tests
uv run ruff check . && uv run mypy           # lint and strict typing
cd app && npm run check                      # frontend type check
```

## Repository layout

```
src/threatwright/      Python core: model, method, rules, library, assistant, render, oscal, vcs, interop, cli, server
  branding.py          product name (single place; app/src/branding.ts for the UI)
  methods/             risk methods as configuration (tr-03183-1)
  libraries/ot/        element, threat, measure templates (CC BY 4.0)
  catalogs/            verified reference IDs (ATT&CK for ICS, EMB3D, IEC 62443 FR, CRA)
  templates/           neutral document templates
  ci_templates/        GitLab/GitHub pipeline templates
  oscal/schemas/       bundled NIST OSCAL schemas
app/                   Svelte 5 + Svelte Flow frontend (bundled into the package)
schemas/               JSON Schemas v1 for all file types
tests/                 unit, roundtrip, rendering, e2e (Playwright, axe)
docs/                  user docs (de), ADRs (en), VERIFY.md
ci/                    static pipeline templates
packaging/             PyInstaller build (portable, no admin rights)
scripts/               repo maintenance (leak checks, library coverage)
```

## Contributing

```
pip install pre-commit && pre-commit install
```

Hooks run gitleaks and a forbidden-files check; CI repeats both over the full history. Security issues: see [SECURITY.md](SECURITY.md).

## License

Code: AGPL-3.0 (see `LICENSE`). Bundled libraries and templates: CC BY 4.0. Your models and generated documents are yours.
