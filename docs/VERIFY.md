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

Library references (MITRE ATT&CK for ICS, EMB3D, IEC 62443) will be added here from M2 on.
