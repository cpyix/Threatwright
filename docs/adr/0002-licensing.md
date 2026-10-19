# ADR-0002: Licensing

Status: accepted

## Context
The tool is open source and may be run as an internal team server. Libraries (elements, threats, measures) should be reusable by other tools and in manufacturers' documents.

## Options
1. Apache-2.0 – maximum adoption, permits closed SaaS forks.
2. AGPL-3.0 – network use triggers source disclosure; protects against closed SaaS forks.

## Decision
- Code: **AGPL-3.0-only** (`LICENSE`).
- Bundled libraries under `libraries/`: **CC BY 4.0**, declared per library in its manifest.
- Generated documents and user project data belong to the user; the tool claims no rights on output (stated in README).
- Third-party content (BSI catalogs, MITRE, IEC) is never bundled unless its license permits redistribution; licenses are documented next to any fixture.

## Consequences
- Dependencies must be AGPL-compatible (checked in CI via SBOM license review).
- Templates shipped as examples are CC BY 4.0 so manufacturers may derive corporate templates freely.
