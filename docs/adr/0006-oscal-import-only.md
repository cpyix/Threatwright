# ADR-0006: OSCAL is import-only

Status: accepted — deviates from brief §10 / M6

## Context
The brief requires OSCAL import and export (component, profile, assessment-results, POA&M, SSP). The owner decided the tool runs locally or on internal servers and needs to **consume** OSCAL only (BSI Grundschutz++ catalog, TR-03183-1 controls).

## Decision
- Supported: `threatwright oscal import <file> --as catalog|profile|component` and `threatwright oscal validate <file>`.
- OSCAL version pinned to the current stable 1.x; official NIST JSON schemas bundled, never fetched at runtime.
- Imported controls become library measures; provenance kept in `oscal_ref` (source document, UUID, control ID); unmapped content kept in `oscal_extra`.
- ARC applicability (TR §6.2) is computed and shown in the UI/documents, not exported as an OSCAL profile.
- **No export**, therefore no custom OSCAL `props` namespace and **no domain needed**. Should export ever be added, a namespace URI need not resolve; the repository URL suffices.
- Object `uuid`s (ADR-0004) are kept so export can be added later without data migration.

## Consequences
- M6 shrinks to catalog/profile/component import, validation, roundtrip import tests and a license-checked Grundschutz++ fixture.
