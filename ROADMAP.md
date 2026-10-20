# Roadmap

Open points after 0.1.0, ordered by impact. Sizes: S = hours, M = days, L = a week or more.

## Next

1. **Approvals with evidence (M).** `Decision` gets `date` and `role`; a rule checks both. The report gets an "Approvals" section with the Git tag and commit. Needs schema version 2, which is also the first real use of `threatwright migrate`.
2. **Quality net (M).** Coverage measurement in CI with a minimum; unit tests for `report.py` and the server's error paths; golden-file tests for document output; request bodies as Pydantic models instead of `dict[str, str]`.
3. **SBOM and vulnerability link (L, most important for 1.0).** Optional `purl` and `version` on elements; CycloneDX SBOM import that links components to elements; optional VEX/CSAF import from files, offline (ADR-0007). New rule: a known vulnerability without threat or measure is an error. Covers CRA Annex I part II for `lifecycle: post_market`.
4. **Method certainty (M).** Clarify the open questions in [VERIFY.md](docs/VERIFY.md) (1–3, 12, 13) with the BSI; record the answers as ADRs and mark open points in the report.
5. **English user documentation (M).** Quick start and tutorial in English.

## Later (after 1.0)

- OSCAL export (SSP or assessment results), revisiting ADR-0006.
- Evidence attachments on measures (file or link instead of free text).
- The qualitative method of TR-03183-1 §5.14.3 as a second method folder.
- Multi-user team server: per-user sessions and access control (ADR-0013 runs one shared session).

## Housekeeping

- ADR-0010 links `docs/methodology.md`; the file is `docs/methodik.md`.
- A `CHANGELOG.md` from 0.1.0 on.
