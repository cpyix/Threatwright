# ADR-0003: Python core, local web UI with Svelte

Status: accepted

## Context
GUI, CLI and CI must share identical loading, validation, scoring and rendering (principle 7). Must run on Windows and Linux without admin rights and offline.

## Options
- Frontend: Svelte + Svelte Flow vs. React + React Flow (both MIT).
- Shell: default browser vs. pywebview window.

## Decision
- Core: Python 3.12+, package `threatwright` with modules `model`, `method`, `rules`, `library`, `render`, `vcs`, `cli`. Pydantic v2, ruamel.yaml, jsonschema, Jinja2 `SandboxedEnvironment`, docxtpl, odfpy, Typer.
- Server: FastAPI bound to `127.0.0.1`, random port, per-session token, strict CSP. Serves the bundled frontend; no CDN.
- Frontend: **Svelte + TypeScript + Svelte Flow**, auto-layout with ELK.js, built with Vite into the Python package.
- Shell: **default browser**. `pywebview` is an optional extra (`threatwright --window`), not a default dependency.
- Product name lives only in `src/threatwright/branding.py` and `app/src/branding.ts`.

## Consequences
- Release builds need Node only at build time; end users need neither Node nor Python (PyInstaller bundle).
- The same server can later be containerised as a self-hosted team server.
