# Produktarten (IoT, Consumer, Software) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Threatwright supports IoT/consumer devices and software as product types next to machines/OT: two new bundled libraries, product type at project creation, wizard texts per product type, and a skippable CRA classification step.

**Architecture:** New libraries `iot` and `software` in `src/threatwright/libraries/`, each self-contained (its threats reference only its own elements and measures) and free of ID collisions with `ot` and each other. Three new reference catalogs with new fixed reference fields, following the existing `attack_ics`/`emb3d`/`iec62443` pattern. Product type = the set of bundled libraries in `ProjectConfig.libraries`. It is chosen at project creation; the model wizard can only add libraries. The classification step lives only in the frontend and persists nothing.

**Tech Stack:** Python 3.12+, Pydantic, FastAPI, Typer, ruamel YAML; Svelte 5 + TypeScript (`app/`); pytest, Playwright e2e (`tests/e2e`).

**Spec:** `docs/superpowers/specs/2026-10-20-produktarten-design.md`

## Global Constraints

- Work on a feature branch or worktree (superpowers:using-git-worktrees). `main` has unrelated uncommitted work, so never commit to `main`.
- Existing projects with `libraries: [ot]` load, validate and report unchanged (ADR-0015; `tests/test_compat.py` stays green without fixture edits).
- No change to the project file schema version, the method, the risk matrix, the rules or the report templates.
- `threatwright init` default stays `libraries: [ot]`.
- Library content in de and en, license CC-BY-4.0, and the same quality bar as `ot`: scenario, consequence, environment, impact, `cra_refs`, ≥1 measure, ≥1 source per threat.
- Size per new library: roughly 30–50 threat templates.
- Catalogs hold identifiers plus own short titles only. No standard text from ETSI or OWASP (OWASP is CC-BY-SA).
- Catalog versions: ETSI EN 303 645 V3.1.3, OWASP ASVS 5.0.0, OWASP MASVS v2 (current at retrieval; record `retrieved:` date and `source:` URL).
- EN 18031 is **not** included. The `iot` library description says radio devices must also consider EN 18031 (RED).
- No MITRE ATT&CK Enterprise/Mobile catalogs in v1.
- CRA classification: wizard only, skippable, nothing stored, not in the report, clearly labelled as orientation and not legal advice, referring to Regulation (EU) 2024/2847 Art. 7, Annex III, Annex IV and the implementing act under Art. 7(4).
- Libraries can only be **added** to an existing project, never removed via GUI.
- UI copy in both languages, in plain wording (the target users are not security specialists).
- Verification before each commit: `uv run ruff check`, `uv run mypy src`, `uv run pytest -q`; frontend: `cd app && npm run check && npm run build`.

## Review Focus

1. **OT project adds `iot`:** combining `ot`+`iot`+`software` must not override any `ot` entry. Expected: zero shared IDs, zero issues. Test in Task 4 (`test_bundled_libraries_do_not_collide`).
2. **A project using only `iot` or only `software`:** every reference must resolve inside that library alone. Expected: `load_libraries([name]).issues == []`. Test in Tasks 2/3 (`test_bundled_library_is_complete_and_valid[...]`).
3. **Unknown or missing library names at creation or add:** `libraries: []`, `["foo"]`, or an attempt to drop `ot` through the add endpoint. Expected: 422 / CLI error, config unchanged. Tests in Task 5 and Task 6.
4. **Project with an own (non-bundled) library in its config:** the wizard's product step shows only bundled types and must not break or offer to remove the own library. Test in Task 6 (`test_add_libraries_keeps_own_library`).
5. **Classification step skipped vs. used:** walking through the step (or skipping it) leaves no trace in model or project files. Test in Task 7 (e2e: model files unchanged after the step).

---

### Task 1: Reference catalogs and fields for ETSI EN 303 645, ASVS, MASVS

**Files:**
- Create: `src/threatwright/catalogs/etsi-303645.yaml`, `src/threatwright/catalogs/asvs.yaml`, `src/threatwright/catalogs/masvs.yaml`
- Modify: `src/threatwright/library.py` (`ThreatTemplate`, `MeasureTemplate`, `_check_integrity`; add constant `CATALOG_NAMES`)
- Modify: `src/threatwright/server.py:454` (catalog allow-list uses `CATALOG_NAMES`)
- Modify: `docs/bibliotheksformat.md` (document the three fields), `docs/adr/0011-library-format.md` (one-line amendment)
- Test: `tests/test_library.py`

**Interfaces:**
- Produces: `CATALOG_NAMES: tuple[str, ...] = ("cra", "attack-ics", "emb3d", "iec62443", "etsi-303645", "asvs", "masvs")` in `library.py`.
- Produces: fields `etsi303645: list[str] = []`, `asvs: list[str] = []`, `masvs: list[str] = []` on both `ThreatTemplate` and `MeasureTemplate`.
- ID formats: ETSI provisions as published (`"5.1-1"`, `"5.3-2"`); ASVS as `"V<chapter>.<section>.<req>"` (`"V6.2.1"`); MASVS as published (`"MASVS-STORAGE-1"`). Catalog format = existing `Catalog` model (`entries: {id: short own title}`).

- [ ] **Step 1: Write the failing test** `test_new_catalog_refs_are_checked(tmp_path)`: an own library in a project with one measure `m` and one threat `t` (`applies_to` an own element) with `etsi303645: ["5.1-1", "NOPE"]`, `asvs: ["V0.0.0"]`, `masvs: ["MASVS-STORAGE-1"]`. Assert the issues contain exactly the locations `own/threat/t.etsi303645` ("unknown reference 'NOPE'") and `own/threat/t.asvs` ("unknown reference 'V0.0.0'"), and nothing for masvs. Also assert `set(CATALOG_NAMES) == {p.stem for p in CATALOGS.glob("*.yaml")}`.
- [ ] **Step 2: Run** `uv run pytest tests/test_library.py::test_new_catalog_refs_are_checked -v`. Expected: FAIL (extra fields forbidden by `Strict`).
- [ ] **Step 3: Implement.** Retrieve the provision/requirement IDs from the official sources (ETSI EN 303 645 V3.1.3 PDF, the OWASP ASVS 5.0.0 and MASVS v2 repos), write the catalogs with own short titles, add the fields, check them in `_check_integrity` by looping over `CATALOG_NAMES` (field name = catalog id without `-`) instead of the hard-coded tuple, and point the server allow-list at `CATALOG_NAMES`.
- [ ] **Step 4: Run** the new test plus `tests/test_library.py tests/test_server.py`. Expected: PASS, OT library still `issues == []`.
- [ ] **Step 5: Commit** `feat(library): ETSI EN 303 645, ASVS and MASVS reference catalogs`.

### Task 2: Library quality test generalised; categories vocabulary

**Files:**
- Modify: `tests/test_library.py` (`test_bundled_ot_library_is_complete_and_valid` → parametrised)
- Modify: `app/src/setup-text.ts` (`CATEGORIES` de/en, new keys before `other`)

**Interfaces:**
- Produces: `BUNDLED = {"ot": (25, 120, 80), "iot": (12, 30, 20), "software": (12, 30, 20)}`, the minimum (elements, threats, measures) per bundled library, used by `test_bundled_library_is_complete_and_valid[name]`. The body is today's OT test (STRIDE coverage per element kind, every threat has a measure and a source, every technical measure is used), plus: every threat has ≥1 `cra_refs`, and every threat has ≥1 ref in `etsi303645` (iot) or in `asvs`/`masvs` (software).
- Produces: new category keys shared by `iot` and `software`. Labels: `device` (Gerät und Firmware / Device and firmware), `wireless` (Funk und Kopplung / Wireless and pairing), `app` (Anwendungen und Apps / Applications and apps), `backend` (Cloud und Backend / Cloud and backend), `distribution` (Auslieferung und Updates / Delivery and updates), `components` (Drittkomponenten / Third-party components). Existing `data`, `network`, `remote`, `media` are reused where they fit.

- [ ] **Step 1:** Parametrise the test over `BUNDLED`; `iot`/`software` fail (library not found). Run `uv run pytest tests/test_library.py -k bundled -v`. Expected: `ot` PASS, others FAIL.
- [ ] **Step 2:** Add the category keys and labels. `cd app && npm run check`. Expected: clean.
- [ ] **Step 3: Commit** (with the test marked `xfail(strict=True)` for `iot`/`software` until Tasks 3/4 remove the mark) `test(library): quality bar for every bundled library`.

### Task 3: `iot` library

**Files:**
- Create: `src/threatwright/libraries/iot/library.yaml`, `elements.yaml`, `threats/*.yaml`, `measures/*.yaml` (split by topic as in `ot`)
- Modify: `tests/test_library.py` (remove xfail for `iot`)
- Test: `tests/test_assistant.py` (one new test)

**Interfaces:**
- Consumes: catalog fields (Task 1), category keys (Task 2).
- Produces: `library.yaml` with `id: iot`, title "IoT- und Consumer-Bibliothek für vernetzte Geräte" / "IoT and consumer library for connected devices", description incl. the EN 18031 note, attribution for ETSI and CRA/TR-03183-1.
- Produces element IDs (other code and tests rely on them): `iot-device` (device), `iot-firmware` (process), `iot-local-ui` (device; buttons/display), `iot-debug-port` (device; UART/JTAG/SWD), `iot-hub` (device; gateway/bridge), `companion-app` (process), `vendor-cloud` (process), `device-api` (process; local REST/CoAP), `ota-service` (process), `pairing` (process; onboarding/provisioning), `iot-credentials-store` (datastore), `user-account` (external), `third-party-service` (external; voice assistant, smart-home platform). Flow types: `flow-wifi`, `flow-ble`, `flow-zigbee-thread`, `flow-matter`, `flow-mqtt-tls`, `flow-https-cloud`.
- Threat coverage (~35–45 templates, own wording) must include at least: default/shared passwords; weak pairing/onboarding (no proof of possession, open setup AP); missing authentication on the local API; unencrypted radio traffic; replay of commands; spoofed cloud endpoint / missing certificate check; unsigned or downgradable OTA; no update path / end of support; debug port left open; firmware extraction and key readout; secrets hard-coded in firmware; cloud account takeover (credential stuffing, no MFA option); IDOR across tenants in the vendor cloud; companion-app insecure local storage; personal data leakage (telemetry, location, presence); missing data deletion on reset/resale; DoS via radio jamming/flooding (with safe-state behaviour); loss of cloud making the device unusable (fail-safe local operation); compromised device as botnet node; insecure third-party integration tokens; tampering with physical controls; insecure factory reset; vulnerable third-party components (SBOM gap); missing vulnerability disclosure contact; logging without security events.
- Measures (~25–35): `iot-unique-credentials`, `secure-pairing`, `local-api-auth`, `radio-encryption`, `replay-protection`, `tls-cert-validation`, `signed-ota`, `anti-rollback`, `support-period-defined`, `debug-port-locked`, `secure-element-keys`, `no-hardcoded-secrets`, `account-mfa`, `tenant-isolation`, `app-secure-storage`, `data-minimisation`, `secure-factory-reset`, `local-fallback`, `rate-limiting`, `sbom-maintained`, `vuln-disclosure-policy`, `security-event-logging`, plus organisational ones as needed. No ID shared with `ot`.

- [ ] **Step 1: Write the failing test** `test_iot_device_gets_suggestions` in `tests/test_assistant.py`: a project with `libraries = ["iot"]`, one element from `iot-device`; the assistant suggestions contain ≥1 template per STRIDE category of the device kind, each referencing `lib:iot/...`. Run it. Expected: FAIL.
- [ ] **Step 2:** Write the library content.
- [ ] **Step 3: Run** `uv run pytest tests/test_library.py tests/test_assistant.py -v`. Expected: `bundled[iot]` and the new test PASS.
- [ ] **Step 4:** `uv run python scripts/library_coverage.py iot` and fix gaps it reports.
- [ ] **Step 5: Commit** `feat(library): iot library for connected and consumer devices`.

### Task 4: `software` library

**Files:**
- Create: `src/threatwright/libraries/software/library.yaml`, `elements.yaml`, `threats/*.yaml`, `measures/*.yaml`
- Modify: `tests/test_library.py` (remove xfail for `software`; add collision test)

**Interfaces:**
- Produces: `id: software`, title "Software-Bibliothek für Desktop-, Mobil- und Backend-Anwendungen" / "Software library for desktop, mobile and backend applications".
- Produces element IDs: `desktop-app`, `mobile-app`, `backend-api`, `web-frontend` (only as a part of the product, e.g. an admin console), `installer`, `updater`, `license-service`, `local-config`, `local-database`, `app-secrets-store`, `os-platform` (external), `third-party-library` (process), `app-user` (external), `admin-user` (external). Flow types: `flow-https-api`, `flow-ipc`, `flow-file-exchange`, `flow-push`.
- Threat coverage (~35–45) must include at least: injection via API input; broken authentication/session handling; broken object-level authorisation; secrets in the client binary; insecure local storage (desktop and mobile); DLL/dylib hijacking and insecure search paths; installer running with excessive rights; unsigned or MITM-able updates; update downgrade; tampered binary / repackaged app; insecure IPC / exported mobile components; deep-link abuse; WebView injection; certificate validation disabled; sensitive data in logs and crash reports; vulnerable dependencies; malicious dependency (supply chain); weak crypto/home-made crypto; missing rate limiting; privilege escalation via a local service; licence check bypass leading to unpatched copies; telemetry leaking personal data; missing secure defaults; missing security update notification to users.
- Measures (~25–35), e.g. `input-validation`, `secure-session-mgmt`, `object-level-authz`, `no-client-secrets`, `os-keystore`, `safe-library-loading`, `least-privilege-install`, `signed-updates`, `update-anti-rollback`, `code-signing`, `ipc-hardening`, `deep-link-validation`, `webview-hardening`, `tls-pinning-or-validation`, `log-redaction`, `dependency-scanning`, `dependency-provenance`, `vetted-crypto`, `api-rate-limiting`, `secure-defaults`, `update-notification`, `sbom-generated`. No ID shared with `ot` or `iot`.

- [ ] **Step 1: Write the failing test** `test_bundled_libraries_do_not_collide`: for each pair of bundled libraries and each kind, the sets of IDs (loaded separately) are disjoint; `load_libraries(["ot", "iot", "software"]).issues == []`. Run it. Expected: FAIL (software missing).
- [ ] **Step 2:** Write the library content.
- [ ] **Step 3: Run** `uv run pytest tests/test_library.py -v`, then `uv run python scripts/library_coverage.py software`. Expected: PASS, no gaps.
- [ ] **Step 4: Commit** `feat(library): software library for desktop, mobile and backend`.

### Task 5: Product type at project creation (core, CLI, server, start page)

**Files:**
- Modify: `src/threatwright/scaffold.py` (`create_project`, zones)
- Modify: `src/threatwright/cli.py:168` (`init_cmd`)
- Modify: `src/threatwright/server.py:436` (`new_project`)
- Modify: `app/src/lib/Start.svelte`, `app/src/i18n.ts`
- Test: `tests/test_cli_tools.py` (or a new `tests/test_scaffold.py`), `tests/test_server_projects.py`

**Interfaces:**
- Produces: `PRODUCT_LIBRARIES: dict[str, tuple[str, str]] = {"ot": ("Maschine oder Anlage", "Machine or plant"), "iot": ("Vernetztes Gerät, IoT, Consumer", "Connected device, IoT, consumer"), "software": ("Software", "Software")}` in `scaffold.py`. The order is the display order.
- Produces: `create_project(path, template="tr", name=None, language="de", libraries: list[str] | None = None) -> Project`. `None` → `["ot"]`. It raises `ValueError` if the list is empty or contains a name not in `PRODUCT_LIBRARIES`, keeps the order of `PRODUCT_LIBRARIES` and drops duplicates.
- Zones: when `"ot"` is not in `libraries`, the third zone is `Z-LAN` "Lokales Netz (LAN/WLAN)" / "Local network (LAN/WLAN)" with `known_network` instead of `Z-PLANT` "Anlagennetz". All other zones stay.
- CLI: `--library/-l` repeatable option, choices = keys of `PRODUCT_LIBRARIES`, default `["ot"]`. `ValueError` → `error: …`, exit 1.
- Server: `POST /api/project/new` accepts optional `"libraries": list[str]` (body becomes `dict[str, Any]`); `ValueError` → 422.
- Start page: checkboxes "Produktart" (one per `PRODUCT_LIBRARIES` entry, `data-testid="new-lib-<id>"`, `ot` pre-checked), with a hint "Mehrfachauswahl möglich, z. B. Gerät mit App" / "Several possible, e.g. a device with an app". The submit button is disabled with none checked.

- [ ] **Step 1: Write failing tests:** `test_create_project_libraries(tmp_path)` → default `["ot"]` with zone `Z-PLANT`; `["software", "iot"]` → `["iot", "software"]` with zone `Z-LAN` and no `Z-PLANT`; `[]` and `["foo"]` raise `ValueError` and create no `threatwright.yaml`. CLI: `init --library iot --library software` writes `libraries: [iot, software]`; `--library foo` exits ≠0. Server: `POST /api/project/new` with `libraries: ["iot"]` → `config.libraries == ["iot"]`; with `[]` → 422.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement** core, CLI and server as specified. Validate before `path.mkdir`.
- [ ] **Step 4: Run** `uv run pytest tests -q --ignore=tests/e2e`. Expected: PASS.
- [ ] **Step 5: Implement** the Start page checkboxes and i18n keys; `npm run check && npm run build`; extend `tests/e2e/test_setup.py` with a second test that creates a project with only `new-lib-iot` checked and asserts that the wizard's component step shows the `setup-type-iot-device` button.
- [ ] **Step 6: Run** `uv run pytest tests/e2e/test_setup.py -v`. Expected: PASS.
- [ ] **Step 7: Commit** `feat: choose product type when creating a project`.

### Task 6: Add libraries from the wizard; wizard texts per product type

**Files:**
- Modify: `src/threatwright/server.py` (new endpoint)
- Modify: `app/src/lib/Setup.svelte` (product step), `app/src/setup-text.ts`
- Test: `tests/test_server.py`, `tests/e2e/test_setup.py`

**Interfaces:**
- Consumes: `PRODUCT_LIBRARIES` (Task 5).
- Produces: `POST /api/project/libraries` with body `{"add": list[str]}`. Names must be in `PRODUCT_LIBRARIES`, else 422. The endpoint appends missing ones in `PRODUCT_LIBRARIES` order after the existing entries, never removes or reorders existing (incl. own) entries, reloads `session.libs`, calls `session.changed()` (written on save; not part of model undo, acceptable because it is add-only) and returns `project_info()`. `GET /api/project` also returns `"product_libraries": list(PRODUCT_LIBRARIES)` so the frontend has no second copy of the names.
- `setup-text.ts`: `product_q` becomes `Record<'ot' | 'iot' | 'software' | 'common', string[]>`. `common` holds the questions on purpose/misuse, users and system boundary; `ot` holds today's OT wording (control cabinet, fieldbus, remote maintenance); `iot` covers the place of installation (home, outdoors, publicly accessible), radio interfaces, app and cloud, and behaviour without internet; `software` covers the platforms (Windows/macOS/Linux, iOS/Android), distribution (store, installer, own updater), backend/API and the users' rights. The wizard shows `common` + the entries of all bundled libraries in the project config. `zones_hint` likewise per type (`ot`: today's sentence; others: "Die vorgeschlagenen Zonen passen für die meisten vernetzten Geräte und Anwendungen …"). Intro and `product_text` lose OT-only wording.
- Product step UI: shows the product types as checkboxes. Checked and disabled = already in the project; unchecked = can be added with a button "Hinzufügen" (`data-testid="setup-add-lib-<id>"`).

- [ ] **Step 1: Write failing tests** in `tests/test_server.py`: `test_add_libraries` → project `[ot]`, add `["iot"]` → `[ot, iot]`, `/api/library` now lists `iot-device`, `dirty` true; adding `["ot"]` again → unchanged; `["foo"]` → 422; `test_add_libraries_keeps_own_library` → config `[own, ot]` (own library from `tests/test_library.py::own_library`), add `["software"]` → `[own, ot, software]`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** the endpoint and the `project_info` field.
- [ ] **Step 4: Run** `uv run pytest tests/test_server.py -v`. Expected: PASS.
- [ ] **Step 5: Implement** the wizard texts and the product-step UI. `npm run check && npm run build`.
- [ ] **Step 6: e2e:** in the iot-only test from Task 5, the product step shows an OT-free guiding question set (assert one iot question visible, the "Schaltschrank" question not visible); clicking `setup-add-lib-software` makes `setup-type-desktop-app` appear in the component step. Run `uv run pytest tests/e2e/test_setup.py -v`. Expected: PASS.
- [ ] **Step 7: Commit** `feat(setup): wizard adapts to product type and can add libraries`.

### Task 7: CRA classification step (orientation only)

**Files:**
- Create: `app/src/cra-class.ts` (data and texts, de/en), `app/src/lib/CraClass.svelte` (step body)
- Modify: `app/src/lib/Setup.svelte` (`STEPS` gets `'s_cra'` at index 1, directly after `s_product`; all `step === N` checks after it shift by one), `app/src/setup-text.ts` (`s_cra` label; intro title "acht Schritten" / "eight steps")
- Test: `tests/e2e/test_setup.py` (existing flow gets one extra `setup-next`), new `tests/e2e/test_cra_class.py`

**Interfaces:**
- `cra-class.ts` exports `SCOPE_EXCLUSIONS: I18n[]` (medical devices MDR/IVDR, vehicle type approval, civil aviation, marine equipment, non-commercial open source, pure SaaS without a product), `CATEGORIES_CRA: { id: string; cls: 'I' | 'II' | 'critical'; label: I18n; examples?: I18n }[]` (Annex III class I items 1–19, class II items 1–4, Annex IV items 1–3, verified against the OJ text of Regulation (EU) 2024/2847, own wording), and `PROCEDURE: Record<'default' | 'I' | 'II' | 'critical', I18n>` (one sentence each: default → module A self-assessment; I → module A only when applying harmonised standards / common specifications / EUCC, otherwise B+C or H; II → B+C or H, or EUCC; critical → European cybersecurity certification where required, otherwise as class II).
- `CraClass.svelte`: local `$state` only, no `api()` call, no prop that writes to `meta`. Three blocks: (1) "Fällt Ihr Produkt unter den CRA?" with the exclusions and a yes/no/unsure answer; (2) "Gehört die Kernfunktion zu einer dieser Kategorien?" as a list of radio options plus "keine davon", with the hint that a connected device (e.g. a thermostat) only falls under Annex III when its *core function* is one of these; (3) result box `data-testid="cra-result"` naming the class and the `PROCEDURE` sentence, and stating that the risk assessment in Threatwright is the same in every case. A permanent notice at the top: orientation only, not a legal assessment, check against the Regulation and the implementing act under Art. 7(4).
- The step can be skipped with the existing "Weiter" button. No extra button needed.

- [ ] **Step 1: Write the failing e2e test** `test_cra_class_is_orientation_only`: open the fixture project's wizard, go to step 2, pick "Smart-Home-Produkte mit Sicherheitsfunktionen" → `cra-result` contains "Klasse I"; pick "keine davon" → contains "Standard". Snapshot all files under the project root (path → bytes) before, click Weiter, save (Ctrl+S) and assert the snapshot is unchanged. Run. Expected: FAIL.
- [ ] **Step 2: Implement** `cra-class.ts`, `CraClass.svelte`, and the step insertion. Update `tests/e2e/test_setup.py` for the shifted steps.
- [ ] **Step 3: Run** `cd app && npm run check && npm run build`, then `uv run pytest tests/e2e -q`. Expected: PASS (all e2e incl. a11y).
- [ ] **Step 4: Commit** `feat(setup): CRA classification as an optional orientation step`.

### Task 8: Wording, docs, roadmap

**Files:**
- Modify: `README.md` (intro sentence, library bullet: "Bibliotheken für OT, IoT/Consumer und Software", counts from the libraries), `docs/schnellstart.md`, `docs/tutorial.md` (product type at creation, classification step), `docs/faq-cyberrisiko.md` (only where it says "machines" exclusively), `docs/bibliotheksformat.md` (list of bundled libraries), `skills/threatwright-model/SKILL.md` (bundled libraries, `--library`), `ROADMAP.md` (Later: EN 18031 mapping once a licensed reviewer is available; ATT&CK Enterprise/Mobile; deeper iot/software libraries driven by user feedback), `src/threatwright/libraries/ot/library.yaml` (unchanged content; only check that its title still reads as one of three)
- Test: none new. `uv run pytest -q` and a grep check.

- [ ] **Step 1:** Rewrite the wording: "manufacturers of products with digital elements, e.g. machines and plants, connected devices, software". OT stays a named, equal case.
- [ ] **Step 2: Check** `grep -rniE "nur für Maschinen|machine and plant manufacturers \(OT\)|für Maschinen- und Anlagenbauer" README.md docs skills`. Expected: hits only where OT is meant specifically.
- [ ] **Step 3:** Run the full suite (`uv run pytest -q`, `uv run ruff check`, `uv run mypy src`, `cd app && npm run check`). Expected: all green. Optionally regenerate screenshots with `uv run python scripts/screenshots.py` if the start page changed visibly.
- [ ] **Step 4: Commit** `docs: Threatwright for machines, connected devices and software`.
