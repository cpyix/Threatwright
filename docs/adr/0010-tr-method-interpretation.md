# ADR-0010: Interpretation of TR-03183-1 in the default method

Status: accepted

## Context
Values were checked against BSI TR-03183-1 v1.0.0 (PDF, 79 pages). The TR offers two ways to evaluate risks: qualitative acceptance criteria (§5.14.3) and a scoring scheme with environment indicator and risk matrix (Annex D), which the TR itself calls "highly experimental". Some details are ambiguous or not specified.

## Decision
1. **Annex D scoring is the default**, as required by the product brief, because it can be computed, compared and checked in CI. The qualitative criteria of §5.14.3 are documented in [`docs/methodik.md`](../methodik.md); a method folder implementing them can be added later without code changes (ADR-0005).
2. **Exposure formula:** `round_half_up(1 + interface × access × user × 4)`. The TR prints `round(1 + i·a·u) * 4` (p. 74), which only yields 4 or 8; p. 78 states the fixed factors 1 and 4 map onto the scale 1–5.
3. **Matrix reading** `inverted` by default (p. 79 assigns the highest risk to "Environment 1" while the formula yields 5 for the worst environment). `literal` stays selectable.
4. **Factors** are taken from Tables 11–13 as printed. The derivation formula on p. 78 (`log_f(b·(f−1)+1)`) does not reproduce the printed factors; the printed values win.
5. **Security assets** (Table 3): an entry like `C'/I'` means "C or I of the protected asset depending on the mechanism". The tool uses the maximum over all listed dimensions of all protected assets (conservative). Users can lower it with a justified amplifier.
6. **Amplifier** (`Impact = BaseImpact × Amplifier`, §5.14.1): applied per C/I/A on an asset, rounded half up and clamped to 1–5. Rounding and clamping are not specified in the TR.
7. **Acceptance:** limit "low" (D.2). Configurable rules: post-market exception for "moderate" (from the D.2 note), stricter limit for safety-related threats and impact +1 for fleet-wide effect (tool conventions, all disabled by default). If several rules apply, the strictest limit wins.
8. **STRIDE → C/I/A** for impact suggestions and **STRIDE per element kind** for coverage are tool conventions, configurable in the method.
9. No BSI text is copied; labels are short own wording.

## Consequences
Items 2, 4, 5, 6, 8 are listed in `docs/VERIFY.md` for confirmation with the BSI (tr-03183@bsi.bund.de).
