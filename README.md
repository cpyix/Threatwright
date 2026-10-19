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

## Development

```
uv sync
(cd app && npm ci && npm run build)          # frontend bundle
uv run threatwright init mein-produkt
uv run threatwright --project mein-produkt   # GUI in the default browser
uv run threatwright validate mein-produkt
uv run pytest                                # incl. GUI end-to-end tests (Playwright)
```

The GUI runs on `127.0.0.1` only, on a random port, protected by a per-start token and a strict Content Security Policy.

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
