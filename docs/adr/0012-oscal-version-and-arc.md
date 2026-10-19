# ADR-0012: OSCAL version, import mapping and ARC applicability

Status: accepted

## Context
ADR-0006 limits OSCAL to import and validation. The import needs a pinned OSCAL version, a defined mapping into the library format (ADR-0011) and a way to evaluate the "Adaptable Risk-based Controls" (ARC) of BSI TR-03183-1 §6 (p. 54-57). The BSI's OSCAL encoding of TR-03183-1 risk scenarios is only available on request (TR §7, p. 58) and could not be checked.

## Decision

### Version and validation
- Pinned: **OSCAL 1.2.3** (usnistgov/OSCAL release v1.2.3, 2026-08-07, latest stable 1.x on 2026-10-19). Bundled JSON schemas for catalog, profile, component-definition and the complete schema in `src/threatwright/oscal/schemas/1.2.3/` (NIST, public domain in the US + CC0 worldwide; README there lists URLs and SHA-256).
- Validation with `jsonschema` Draft-07 (the schemas declare draft-07). The registry has no retrieval: any non-local `$ref` fails instead of fetching (ADR-0007). Format checks use the formats `jsonschema` knows without extra packages; the schemas' own regex patterns do the real date/URI checks.
- **Deviation:** the NIST token pattern uses `\p{L}` and `\p{N}`, which Python `re` does not support. They are translated to `[^\W\d_]` (Unicode letter) and `\d` (Unicode decimal digit). `\p{N}` also covers other numerics (e.g. Roman numeral characters); such ids are reported as invalid. Accepted gap.
- JSON only; XML and YAML get a clear "not supported, convert to JSON" error. Size limit 50 MB. Models other than catalog/profile/component-definition are reported as unsupported but still validated against the complete schema.
- Documents declaring an older `oscal-version` (e.g. the BSI's 1.1.3) are validated against 1.2.3; this works for the checked BSI files.
- **Schema quirk:** in the 1.2.3 JSON schema `imports[].href` of a profile is not required (anyOf without `href`); the importer tolerates its absence.

### Mapping (field names checked against the 1.2.3 schema)
- Catalog → project library `libraries/<slug>/`: `library.yaml`, `measures/<id>.yaml` (one file per control, because the YAML loader limits files to 1 MB and per-entry files keep diffs small), and a byte copy of the input in `source/<name>.json` (keeps group data, back-matter and everything else not mapped).
  - Every control incl. nested controls (enhancements) becomes a `MeasureTemplate`; id = control id lowercased, other characters → `-`, uniqueness by suffix `-2`, `-3`.
  - `title.de` = `title.en` = control title: OSCAL JSON has no document language field.
  - `description` = statement prose incl. nested items ("label prose", indented); `{{ insert: param, id }}` is replaced by the parameter's `values`, else `[choice | choice]`, else `[label]`, else `[id]`.
  - `kind: organizational` for every imported control: catalogs carry no reliable technical/organizational marker; users override in their own library.
  - `category` = group path "`<id> <title> / ...`"; `oscal_ref` = {source: "title version", uuid: catalog uuid, control_id}; `controls` = [{catalog_uuid, control_id}].
  - `oscal_extra` = the control object without `id`, `title`, `controls`; so a control can be rebuilt exactly from its entry (tested). Keys with an underscore are added by Threatwright (`parent_control`, `control_ids`); hyphenated keys are OSCAL.
  - Manifest: version = `metadata.version`; license = `metadata.props[name=license]`, else `metadata.links[rel=license].href`, else "see source"; attribution = source label, catalog uuid with OSCAL version, party names.
- Re-import: unchanged entries are written byte-identically; changed entries get `rev + 1` (`library update` shows them). `oscal_ref.source` is ignored in this comparison because it carries the document version. Removed controls are deleted. A library folder without `source/` is never overwritten.
- Component definition → library with `elements/<id>.yaml` (one file per component, same reasons). Kind mapping from `type`: software, service → process; hardware, physical → device; interconnection → flow; everything else → device. `oscal_extra` = component without uuid/title/description plus `control_ids` from all implemented requirements.
- Profile → `profiles/<slug>.yaml` (own schema, see docs/oscal.md). Imports are resolved to imported catalog libraries via back-matter rlink hash, file name or resource title.
- Path safety: library/profile names must match the library id pattern, are not Windows device names, and must resolve directly below `libraries/` or `profiles/`. Entry file names avoid Windows device names (`x-con.1.yaml`).

### ARC applicability (TR §6.2, p. 54)
- A control applies to the model if any part of it (element in a zone, or assessed threat) handles an asset whose base impact (incl. inheritance and amplifier, `method.asset_impact`) reaches the scenario minimum in at least one listed dimension, and each listed environment parameter contains the part's value or `*`. Missing parameters match anything.
- Optional `combined=True` evaluates the §6.3 (p. 54-55) combined risk profile: all assets of the model with the union of all environments.
- Assets handled by an element: assets of flows starting or ending there and assets of threats targeting it. Element environment = its zone's environment.
- **Assumption — risk scenario encoding:** a control part with `name: risk-scenario`, `prose` = scenario text, props
  `asset-impact` (`C(3)` or `C:3`, repeatable), `asset-class` (optional, exact match, repeatable), `interface-restriction`, `access-restriction`, `user-capability` (repeatable; TR wording such as "External network" is normalised to the method keys, e.g. `external_network`; `*` = any). Unparseable `asset-impact` values are ignored (the scenario then matches more broadly — the conservative direction). Library YAML uses the same structure under `oscal_extra.parts`. To be revisited when the BSI encoding is available.
- **Interpretation:** "at least the impact listed" with several dimensions (TR example C(3) I(3) A(3), p. 55) is read as "any one of them"; the example's own wording "impact of at least 3" supports this.
- Manual decisions are stored in `profiles/arc-overrides.yaml` (model → library measure id → {applies, rationale, by}); no model schema change.

## Consequences
- A future OSCAL 1.x release is a data change: add the schema folder, switch `OSCAL_VERSION`, re-run the tests.
- If the BSI publishes a different risk-scenario encoding, only `arc.risk_scenarios` needs to change.
