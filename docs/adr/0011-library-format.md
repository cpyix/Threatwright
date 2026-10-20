# ADR-0011: Library format and reference catalogs

Status: accepted

## Context
Libraries hold element types, threat and measure templates (brief §6). Projects activate several libraries, override single entries and must learn when a copied entry changed upstream. References to MITRE ATT&CK for ICS, MITRE EMB3D, IEC 62443 and the CRA must not be invented.

## Decision
- A library is a folder with `library.yaml` (id, version, license, attribution) and any YAML files with top-level lists `elements:`, `threats:`, `measures:`. Grouping into files is free; the bundled `ot` library groups by topic.
- Entries have a stable `id` and an integer `rev`, raised on every content change. Copied model objects store `library_ref: lib:<library>/<kind>/<id>@<rev>`. `library update` and the `library-outdated` warning compare the recorded revision with the current one.
- Projects list libraries in `threatwright.yaml`; later libraries override entries with the same kind and id. A project folder `libraries/<name>` wins over a bundled library of the same name.
- Links are stored once: threats declare `applies_to` (element types) and `measures`; element types do not list threats.
- **Reference catalogs** in `src/threatwright/catalogs/` list every allowed external ID: ATT&CK for ICS (v20, retrieved 2026-10-19), EMB3D threats, IEC 62443 FR1–FR7, CRA Annex I/II and Art. 13/14 (mapped to TR-03183-1 Annex B IDs). Library integrity checks reject IDs outside these lists. IEC 62443 SR/CR numbers are not used because the standard is not freely available for verification. Amendment: ETSI EN 303 645 V3.1.3 provisions, OWASP ASVS 5.0.0 requirements and OWASP MASVS v2 controls are catalogs too (`etsi-303645`, `asvs`, `masvs`; fields `etsi303645`, `asvs`, `masvs`).
- Library texts use block-style YAML for prose (flow style breaks on commas).

## Consequences
- Updating a catalog (new ATT&CK version) is a data change plus re-check of library references.
- ATT&CK v20 replaced several IDs (e.g. T0855 → T1692, T0812/T0891 → T1694, T0839/T0857 → T1693); libraries written against older versions fail the integrity check until updated, which is intended.
