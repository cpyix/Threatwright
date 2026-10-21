# Roadmap

Open points after 0.4.0, ordered by impact. Sizes: S = hours, M = days, L = a week or more. Released changes are in [CHANGELOG.md](CHANGELOG.md).

## Next

1. **Reporting assistant for CRA Art. 14 (M).** From a linked vulnerability, draft the early warning (24 h), the notification (72 h) and the final report, prefilled with the affected elements and measures.
2. **Quality net (M).** Coverage measurement in CI with a minimum; unit tests for `report.py` and the server's error paths; golden-file tests for document output; request bodies as Pydantic models instead of `dict[str, str]`.
3. **Method certainty (M).** Clarify the open questions in [VERIFY.md](docs/VERIFY.md) (1–3, 12, 13) with the BSI; record the answers as ADRs and mark open points in the report.
4. **Security assets of building blocks (S).** Library elements bring security assets (keys, logs) without `protects`, which `security-asset-without-protects` reports right away; link them to the element's other assets when the element is created (the example projects already do).
5. **Open measures as issues (S–M).** A CI job that creates or updates GitLab/GitHub issues from measures with `owner` and `due`.
6. **SPDX SBOMs (S).** Read SPDX JSON next to CycloneDX (ADR-0016).

## Later (after 1.0)

- OSCAL export (SSP or assessment results), revisiting ADR-0006.
- The qualitative method of TR-03183-1 §5.14.3 as a second method folder.
- EN 18031 mapping for radio devices in the `iot` library, once a licensed reviewer is available.
- MITRE ATT&CK Enterprise and Mobile as additional reference sets.
- Deeper `iot` and `software` libraries, driven by user feedback.
- Multi-user team server: per-user sessions and access control (ADR-0013 runs one shared session).
- Rerouting a single connection around obstacles without a full auto layout (libavoid or a small grid router).
