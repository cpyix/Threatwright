# ADR-0004: Git as database, one YAML file per object

Status: accepted

## Context
Every change must be reviewable via merge requests (RH_UPD.1). Several developers edit the same model in parallel.

## Decision
- Project = folder (optionally a git repo). One YAML file per object (`models/<m>/threats/T-0001.yaml`), diagram positions separate in `diagram.layout.yaml`.
- Files carry `schema_version`; JSON Schemas under `schemas/` are generated from the Pydantic models and committed.
- Each object has a human ID (`T-0001`, tool-assigned, configurable prefix) and an immutable `uuid` (v4).
- ruamel.yaml in safe round-trip mode: comments preserved, deterministic key order (schema order), UTF-8, LF, no timestamps. Read tolerates CRLF. Size and nesting limits on load.
- Derived values (exposure, risk, acceptance) are never stored.
- Stored enum values are English identifiers (`status: assessed`, not `bewertet` as in the brief's example); the UI translates them. Keeps files language-neutral when a team mixes de/en.
- Fields at their default value are not written into new files; fields already present in a file are kept even when they equal the default. Saving only writes files whose content changed.
- Values defined by the method (interface, access, user, asset class) are plain strings in the schema and are checked against the method by the rules engine (ADR-0005).
- No model data in localStorage/IndexedDB/SQLite.

## Consequences
- Load → save without edits must produce zero diff; enforced by a roundtrip test over all fixtures on Windows and Linux.
- Schema migrations are explicit (`threatwright migrate`) and produce readable diffs.
