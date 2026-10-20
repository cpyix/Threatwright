# ADR-0015: Compatibility of projects across releases

Status: accepted

## Context
Threat models live for the whole support period of a product, often many years. A project created with one release must open in every later release without manual work, and nothing may be misread silently.

## Decision
- **Schema version per file.** Every project file carries `schema_version` (`SCHEMA_VERSION` in `model/objects.py`). It only rises when the file format changes incompatibly; additive, optional fields need no new version.
- **Migration chain.** `model/migrations.py` holds one step per version (`MIGRATIONS[n]` turns version n into n + 1). Loading runs the missing steps in memory on the YAML document, so comments survive. The files change on the next save in the GUI or with `threatwright migrate`. Validation and CI work on old files without rewriting them.
- **Newer files are refused.** A file with a higher `schema_version` than the release knows is reported as "written by a newer Threatwright; please update" and not loaded. `threatwright migrate` writes nothing while any file fails to load.
- **Compatibility corpus.** Before each release, `scripts/compat_snapshot.py` stores a sample project of that release under `tests/fixtures/compat/v<version>/`. `tests/test_compat.py` checks on every change that all of them load without issues, keep their references (no structural validation errors), survive a save unchanged and still render documents. A sample is never regenerated or edited afterwards.
- **Stable references.** Library entries (`library_ref`) and catalog IDs are never deleted or renamed; outdated entries are marked, and `library-outdated` points to newer versions. A change to a risk method gets a new method id or version, so existing projects keep their assessment until someone switches deliberately.
- **Autosave snapshots** (ADR-0014) store `schema_version` per object and run the same migration on restore.

## Consequences
- Every format change comes with a migration step and keeps the corpus green; CI enforces it.
- Downgrades are not supported: once a project is saved with a newer schema, older releases refuse it with a clear message instead of corrupting it.
- The corpus contains neutral demo models built only from library building blocks, no product data.
