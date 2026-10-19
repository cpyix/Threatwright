# Threatwright

Local-first threat modelling and risk analysis for products with digital elements under the EU Cyber Resilience Act, following **BSI TR-03183-1**. Aimed at machine and plant manufacturers (OT). Status: **pre-alpha** (M1: method, validation, CLI).

- Runs offline on Windows and Linux, no admin rights, no network access.
- Models are YAML files in your git repo — merge requests are the change history.
- Documents (DOCX, ODT, Markdown, HTML, PDF via LibreOffice) from your own templates.
- Same core for GUI, CLI and CI (GitLab/GitHub pipeline templates).

Architecture decisions: [`docs/adr/`](docs/adr/). Methodik: [`docs/methodik.md`](docs/methodik.md), Prüfregeln: [`docs/pruefregeln.md`](docs/pruefregeln.md).

```
uv sync
uv run threatwright init mein-produkt
uv run threatwright validate mein-produkt
```

## Planned repository layout

```
src/threatwright/      Python core: model, method, rules, library, render, vcs, cli, server
  branding.py          product name (single place)
  ci_templates/        GitLab/GitHub pipeline templates (rendered per project)
  methods/tr-03183-1/  risk method as configuration (BSI TR-03183-1)
app/                   Svelte + Svelte Flow frontend (bundled into the package)
schemas/               JSON Schemas v1 (generated from the Pydantic models)
libraries/ot/          element, threat, measure libraries (CC BY 4.0)
templates/             neutral document templates
tests/                 unit, roundtrip, rendering; e2e/ (Playwright)
docs/                  ADRs, user docs, VERIFY.md, template reference
ci/                    copies of the pipeline templates for manual use
scripts/               repo maintenance (leak checks)
```

## Contributing

```
pip install pre-commit && pre-commit install
```
Hooks run gitleaks and a forbidden-files check; CI repeats both over the full history.

## License

Code: AGPL-3.0 (see `LICENSE`). Bundled libraries and example templates: CC BY 4.0. Your models and generated documents are yours.
