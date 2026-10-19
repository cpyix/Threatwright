# Open verification items

Values and interpretations that are not (or not unambiguously) backed by a primary source. Reference: BSI TR-03183-1 v1.0.0, PDF of July 2026, 79 pages. Each item stays here until confirmed or corrected.

| # | Item | Where | Status |
|---|------|-------|--------|
| 1 | Exposure formula: `*4` moved inside the rounding (printed bracket typo, p. 74) | `methods/tr-03183-1/method.yaml` `exposure` | interpretation, see ADR-0010 |
| 2 | Matrix reading `inverted` vs. printed `literal` (p. 79) | `risk_matrix.matrix_row_from_exposure` | interpretation, configurable |
| 3 | Factor derivation formula (p. 78) does not reproduce Tables 11–13; printed factors used | `interface`, `access`, `user` | printed values used |
| 4 | Security asset `C'/I'` resolved as maximum of protected assets | `asset_classes.Security.*` | tool convention |
| 5 | Amplifier: rounding half up and clamping to 1–5 | `method.py` `asset_impact` | tool convention |
| 6 | STRIDE → C/I/A mapping for impact suggestions | `stride_impact` | tool convention |
| 7 | STRIDE categories per DFD element kind (coverage) | `stride_per_kind` | tool convention |
| 8 | Acceptance rules `safety-stricter`, `fleet-wide-amplifier` | `acceptance.rules` | tool convention, disabled |
| 9 | German labels of scales and indicators | `method.yaml` | own translation |
| 10 | Table 1 lists `PII.Important` twice (p. 46 and 47) with identical values | `asset_classes` | no impact |

## Library references

External IDs in libraries are restricted to the catalogs in `src/threatwright/catalogs/` (integrity check):

| Catalog | Verified against | Date |
|---|---|---|
| ATT&CK for ICS | attack.mitre.org/techniques/ics (v20) | 2026-10-19 |
| EMB3D | emb3d.mitre.org/threats | 2026-10-19 |
| CRA Annex I | BSI TR-03183-1 v1.0.0 Annex B, Tables 8–10 (p. 60–64); point (g) text not in the extracted table, ID confirmed by the list on p. 57 | 2026-10-19 |
| IEC 62443 | only FR1–FR7; SR/CR numbers deliberately not used | — |

## OSCAL and ARC (see ADR-0012)

| # | Item | Status |
|---|------|--------|
| 11 | OSCAL pinned to 1.2.3; NIST schema regex `\p{L}`/`\p{N}` translated for Python | implementation detail, tested |
| 12 | Encoding of ARC risk scenarios in OSCAL (part `risk-scenario`, props `asset-impact`, `interface-restriction`, ...) | assumption: the BSI format for TR-03183-1 controls is not public; confirm with tr-03183@bsi.bund.de |
| 13 | ARC applicability rule (TR §6.2, p. 54) and combined profiles (§6.3) | own reading of the TR text |
| 14 | Grundschutz++ excerpt (CC BY-SA 4.0) used as test fixture with NOTICE | licence checked |

Open: whether each library entry's ATT&CK/EMB3D mapping is the best fit is a domain judgement, not a fact; review welcome.
