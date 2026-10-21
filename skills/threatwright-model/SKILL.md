---
name: threatwright-model
description: Create or edit a Threatwright threat model by editing its YAML files directly (no GUI). Use when the user wants to build or change a threat and risk analysis after BSI TR-03183-1 / the EU Cyber Resilience Act in a Threatwright project folder, add elements, data flows, assets, threats, measures or open questions, assess risks, or fix `threatwright validate` findings.
---

# Threatwright: edit threat models as files

Threatwright is a local-first tool for threat modelling and risk analysis of products with digital elements under the EU Cyber Resilience Act (CRA), following **BSI TR-03183-1**. A project is a folder of plain YAML files, one file per object, kept in Git. The GUI, the CLI and CI all read and write the same files, so you can edit them directly. This skill describes the files and the workflow.

## Rules that always apply

1. **The files are the source of truth.** If the GUI has the project open, make sure it has no unsaved changes first; it notices changes on disk and reloads.
2. **Run `threatwright validate <project>` after every change** and fix every error. Exit code 1 means errors.
3. **One object per file**, file name = `id` + `.yaml`, e.g. `models/main/threats/T-0007.yaml`.
4. **Never change an existing `id` or `uuid`** by hand. A new object gets a new, unused id (next free number of its prefix) and a fresh random UUID v4.
5. Every file starts with `schema_version: 1`. Do not raise it; `threatwright migrate` handles format upgrades.
6. **Do not invent facts.** No made-up CRA references, evidence, owners, approvals or acceptance decisions. Leave a field empty or create an open question (`questions/Q-…`) instead.
7. **Rule 3.3 (cyber cause):** a threat is a cybersecurity risk only if its cause is an attack on the digital product (unauthorised access; manipulation of data, commands, configuration or software; data leakage; disruption by digital means). Decide per threat and explain in `scenario`; never set `cyber_cause: true` in bulk on threats you wrote yourself. A threat adopted from a library template gets `cyber_cause: true`: every template describes an attack, and adopting it (also several at once) is the per-threat decision. Reject it instead if the template does not fit the product. Not a cyber risk: set `cyber_cause: false`, `status: rejected` and a `rejection` with rationale.
8. Do not edit `.threatwright-history/` (local autosave versions) or `build/` (generated documents). `diagram.layout.yaml` only holds positions; new elements may stay out of it (the GUI places them).
9. Write UTF-8, keep YAML comments, and keep the user's language (`language` in `threatwright.yaml`) for titles and texts.

## Project layout

```
my-product/
  threatwright.yaml            project: name, method, language, libraries, lifecycle,
                               support_until and next_review (dates, only from the user)
  custom-fields.yaml           optional extra fields per object type
  method-overrides.yaml        optional project overrides of the risk method
  models/
    main/                      one folder per model (lowercase name)
      model.yaml               title, description, zones, configurations, changelog
      diagram.layout.yaml      node positions only
      elements/E-0001.yaml     components, software, data stores, external entities
      flows/F-0001.yaml        data flows between two elements
      assets/A-0001.yaml       what is worth protecting
      threats/T-0001.yaml      threats with assessment
      measures/M-0001.yaml     countermeasures
      questions/Q-0001.yaml    open questions
```

Create a project with `threatwright init my-product --name "My product" --language en` (template `tr` is the TR-03183-1 default with four zones; the OT library is the default). Choose the product type with `--library`/`-l ot|iot|software` (repeatable, e.g. `-l iot -l software`); without `ot` the third zone is `Z-LAN` (local network, LAN/WLAN).

Id prefixes: `E` elements, `F` flows, `A` assets, `T` threats, `M` measures, `Q` questions; ids look like `T-0007` (pattern `^[A-Za-z][A-Za-z0-9_]*-[0-9]{4,}$`).

## File formats

### model.yaml: zones and configurations

```yaml
schema_version: 1
title: Packaging machine
uuid: 1b4e…                       # keep
description: |
  Purpose, intended use, operating environment and system boundary (CRA Art. 13(3)).
configurations:                   # product variants ("Ausbaustufen / Varianten")
  - {id: K-A, title: Standard}
  - {id: K-B, title: With remote service}
zones:                            # trust zones; the environment sets the exposure
  - id: Z-INTERNAL
    title: Device internal
    environment: {interface: physical, access: restricted, user: non_user_related}
  - id: Z-EXTERNAL
    title: External network
    environment: {interface: external_network, access: non_restricted, user: skilled}
cra_not_applicable:               # CRA Annex I requirements that do not apply, rationale required
  AI-I-2-m: The device stores no user data or settings.
```

`threatwright validate` warns about every Annex I requirement (`AI-…` in the CRA catalog) that no threat or measure references and that is not in `cra_not_applicable` (`cra-requirement-uncovered`). Only mark a requirement as not applicable when the user confirms the reason.

Environment values (TR-03183-1 Annex D):
- `interface`: `physical`, `local`, `dedicated_known_network`, `known_network`, `external_network`
- `access`: `restricted`, `public_restricted`, `movable`, `non_restricted`
- `user`: `non_user_related`, `skilled`, `instructed`, `layman`

### Element

```yaml
schema_version: 1
id: E-0001
uuid: 3f94b57d-bde9-49e6-9efe-89853db3ba0a
title: Machine controller
library_ref: lib:ot/element/plc@1     # optional: library building block it came from
kind: device                          # process | device | datastore | external
zone: Z-INTERNAL
configurations: []                    # empty = all variants
sbom: [firmware.cdx.json]             # optional: CycloneDX files in <project>/sbom/
stride_not_relevant:                  # optional, rationale required
  R: No user actions on this device; logging happens in the HMI.
```

### Flow

```yaml
schema_version: 1
id: F-0002
uuid: …
title: EtherCAT
library_ref: lib:ot/element/fieldbus-ethercat@1
source: E-0001
target: E-0002
protocol: EtherCAT
bidirectional: false
assets: [A-0004]                      # assets transported
```

A flow whose source and target are in different zones crosses a trust boundary; that is where most threats belong.

### Asset

```yaml
schema_version: 1
id: A-0003
uuid: …
title: Machine parameters (Machine controller)
asset_class: BusinessData.Important
protects: []                          # only for Security.* assets: what they protect
amplifier:                            # optional deviation from the class, rationale required
  i: 1.2
  rationale: Wrong parameters can damage the machine.
```

Asset classes (TR-03183-1 tables 1–3): `BusinessData.Generic`, `BusinessData.Important`, `Functions.CommunicationLocal`, `Functions.CommunicationNetwork`, `Functions.Essential`, `Functions.NonEssential`, `Functions.Safety`, `Other.Configuration`, `Other.Telemetric`, `PII.Generic`, `PII.Important`, `PII.TechnicalNecessary`, `Security.Logs`, `Security.Mechanism`, `Security.PublicConfiguration`, `Security.Secrets`.

### Threat

```yaml
schema_version: 1
id: T-0001
uuid: bdcdd40e-a92f-4c12-ac3d-4974ce039308
title: Rogue master takes over fieldbus Machine controller
library_ref: lib:ot/threat/fieldbus-rogue-master@1
stride: [S, T]                        # S T R I D E
targets: [E-0001]                     # elements and/or flows
assets: [A-0003]
cyber_cause: true                     # rule 3.3, see above
scenario: >-
  The fieldbus has no authentication of the master. An attacker connects …
consequence: >-
  The attacker sets outputs, moves drives …
safety_related: true
assessment:                           # before measures
  interface: local                    # pre-filled from the target's zone, adjust if needed
  access: restricted
  user: non_user_related
  impact: 5                           # 1–5, highest affected asset, your decision
  rationale: …
residual:                             # optional: after measures, same fields
  interface: local
  access: restricted
  user: non_user_related
  impact: 2
measures: [M-0001, M-0002]
questions: []
cra_refs: [AI-I-2-d, AI-I-2-f]        # ids from the CRA catalog only
vulnerabilities: []                   # vulnerability ids this threat treats, e.g. CVE-2024-0001
status: identified                    # identified | assessed | treated | accepted | rejected
acceptance:                           # only with status accepted; only what the user tells you
  by: <name given by the user>
  role: <role, e.g. Product Owner>     # approvers in the method may be names or roles
  date: 2026-10-01                     # day of the decision, YYYY-MM-DD
  rationale: …
rejection:                            # only with status rejected
  by: <optional>
  date: <optional>
  rationale: …
```

Exposure and risk are **computed**, never stored: exposure from interface × access × user, risk 1 (very low) to 5 (very high) from the TR matrix. Up to "low" is acceptable; above that the threat needs measures (`treated`, with a `residual` assessment) or an approved acceptance. Status `assessed` or later requires a complete assessment (interface, access, user, impact).

### Measure

```yaml
schema_version: 1
id: M-0001
uuid: …
title: Restrict physical access to the fieldbus
kind: technical                       # technical | organizational | design | user_information | supply_chain
compensating: false
owner: null                           # only if the user names one
status: proposed                      # proposed | decided | in_progress | implemented
due: null                             # YYYY-MM-DD
evidence: null                        # only real evidence (document, test, link)
evidence_refs: []                     # https links or files under <project>/evidence/, e.g. evidence/pentest-2026.pdf
cra_refs: []
```

Several threats may share one measure: reference the existing id instead of duplicating it.

### SBOMs and vulnerabilities

CycloneDX JSON SBOMs live in `<project>/sbom/`, vulnerability statements (CycloneDX VEX, CSAF) in `<project>/vulnerabilities/`. Never write or edit these files yourself: they come from the user's tools. `threatwright vulnerabilities <project>` lists every vulnerability per element. Each one with state `affected` or `under_investigation` needs a threat on that element with the id in `vulnerabilities` (error `vulnerability-untreated`); see `docs/sbom.md`.

### Question

```yaml
schema_version: 1
id: Q-0001
uuid: …
title: Is the service port disabled in the field?
addressee: Hardware team
status: open                          # open | answered
answer: null
threats: [T-0004]
```

## Workflow for a new or extended model

1. **Scope:** fill `description` in `model.yaml` (purpose, intended use, environment, system boundary). Check the zones and set `environment` for each.
2. **Elements:** one file per component; choose `kind` and `zone`. Prefer library building blocks (see below) and keep their `library_ref`.
3. **Flows:** connect the elements; set `protocol` and `assets`.
4. **Assets:** what each element or flow holds or provides; choose the `asset_class`.
5. **Threats:** go through STRIDE per element and flow. For each relevant category write a threat with a concrete attack path (one attack path = one threat), or record `stride_not_relevant` with a rationale on the element/flow. Decide rule 3.3 per threat.
6. **Assess:** environment from the zone, impact from the affected assets. Set `status: assessed`.
7. **Measures:** for every threat above "low", link measures and add a `residual` assessment; `status: treated`. Open points become questions.
8. `threatwright validate`, then fix errors; warnings such as `coverage-gap` show remaining work.
9. Documents: `threatwright build my-product --format docx` (or `md`, `html`, `odt`, `pdf`).

## Library building blocks

Projects use the bundled libraries listed in `libraries:` (`ot` for machines and plants, `iot` for connected devices with ETSI EN 303 645 references, `software` with OWASP ASVS/MASVS references; the examples below use `ot`). A library provides element types, threat and measure templates. In an installed Threatwright the files are in the package folder `threatwright/libraries/ot/` (`elements.yaml`, `threats/*.yaml`, `measures/*.yaml`). A template has `id`, `rev`, `stride`, `applies_to` (element types), bilingual `title`/`scenario`/`consequence` with an `{element}` placeholder, `impact`, `measures` and `cra_refs`.

When you adopt a template, copy its texts in the project language, replace `{element}` with the target's title, set `library_ref: lib:ot/threat/<id>@<rev>` (elements: `lib:ot/element/<id>@<rev>`, measures: `lib:ot/measure/<id>@<rev>`) set `cyber_cause: true` (see rule 7) and still decide the assessment for this product. `threatwright library update <project>` lists objects whose template has a newer revision.

## Renaming and deleting

- Prefer renaming ids in the GUI (it updates every reference). By hand: rename the file, change `id`, and replace the id in every `targets`, `assets`, `measures`, `questions`, `threats`, `source`, `target`, `protects` list and in free text.
- Deleting: remove the file and every reference to its id; `validate` reports leftovers as `unresolved-ref`.

## Useful commands

```
threatwright validate my-product                 # all rules (see docs/pruefregeln.md)
threatwright build my-product --format md        # documents into my-product/build
threatwright diff v1.0 --path my-product         # semantic changes since a Git tag
threatwright migrate my-product                  # upgrade files written by an older release
threatwright --project my-product                # open the GUI to check the diagram
```

Further reading in the repository: `docs/methodik.md` (method), `docs/pruefregeln.md` (rules), `docs/faq-cyberrisiko.md` (rule 3.3), `docs/bibliotheksformat.md` (library format).
