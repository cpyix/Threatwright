# ADR-0005: Methodology as configuration

Status: accepted

## Context
TR-03183-1 is the default, but scales, factors, matrix and acceptance rules must be overridable per project and replaceable by other methods without code changes.

## Decision
- `methods/<method-id>/` holds scales, asset classes, environment factors, exposure formula parameters, risk matrix and acceptance rules as YAML; every value carries a source (section/table/page) or `verify: true`.
- Projects reference a method in `threatwright.yaml` and may override via `method-overrides.yaml`.
- The scoring engine interprets the config; no TR numbers in code.
- Known inconsistency (Annex D): formula yields E=5 for the worst environment, printed matrix puts "Environment 1" at highest risk. Config key `matrix_row_from_exposure: literal | inverted`, default **`inverted`**, with a visible notice in GUI and documents. A test asserts: internet-facing attack on a safety function ⇒ "very high" under `inverted`.

## Consequences
- Values unverified against TR v1.0.0 are listed in `docs/VERIFY.md` until checked against the primary source.
