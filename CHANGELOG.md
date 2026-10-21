# Changelog

Projects from earlier releases open unchanged (ADR-0015); all new fields are optional, so the file format stays at schema version 1. Older releases refuse files that use a new field.

## Unreleased

### Control software on embedded Linux

- **Processes on a host.** `runs_on` places a process (or a virtual device) on a device of the same model; without its own zone it takes the host's zone. `privilege` (`kernel`, `root`, `service`, `user`, optional account and capabilities) gives it a rights context; a flow between two contexts on the same host is a boundary crossing like one between zones: dotted in the diagram, column "Boundary" in the reports, warning `privilege-boundary-gap`.
- **Sub-models.** `refines: <model>/<id>` lets an element of a sub-model refine an element of another model. One assessment per product: the parent's document contains the sub-model (ids as `software/T-0003`), risk distribution, traceability, approvals and CRA coverage count both, `build` renders no separate document for the sub-model, and threats on either side cover the other ([docs/methodik.md](docs/methodik.md#teilmodelle-und-rechtekontexte)).
- **Technical attack surface.** `listens_on`, `authentication`, `memory_safe` and `sbom_ref` (purl/CPE) on elements, shown in a new report table.
- **New rules.** Errors `runs-on-invalid`, `runs-on-cycle`, `refines-unresolved`, `refines-multiple-parents`, `refines-cycle`; warnings `exposed-service-unauthenticated`, `privilege-boundary-gap`, `host-takeover-understated`, `duplicate-assessment`, `sbom-ref-invalid` ([docs/pruefregeln.md](docs/pruefregeln.md)).
- **Library `embedded-linux`.** Element, threat and measure templates for control software on a Linux industrial PC (processes, OS services, kernel and modules, shared memory, update staging, local IPC, SSH, people with system access); builds on `ot` (`requires` in `library.yaml`). `threatwright init -l embedded-linux --example` creates a machine model with a refining sub-model `software`.
- **Diagram.** Hosts and their privilege contexts are framed; auto layout keeps a host's processes together inside its zone.
- **Palette filter.** The building block palette can be filtered by library (product type) once more than one is active.

## 0.4.1

- **SVG export matches the canvas.** "Export SVG" in the diagram now saves the diagram exactly as drawn, including chosen sides, bend points and icons, as plain SVG without embedded HTML, so Word, PowerPoint and Inkscape show it too.
- **Well-formed SVG for external entities.** The server-side SVG (report, `/diagram.svg`) no longer writes a duplicate `stroke` attribute for external entities, which strict XML readers rejected.

## 0.4.0

### CRA evidence

- **CRA requirements (Annex I).** New view and report section `cra_requirements`: for each essential requirement, the threats and measures that address it, with status implemented, measure planned, threat only, open or not applicable. Not applicable needs a rationale (`cra_not_applicable` in `model.yaml`). New warning `cra-requirement-uncovered` once a model has threats.
- **SBOMs and vulnerabilities.** CycloneDX SBOMs in `sbom/` are assigned to elements (`sbom`); CycloneDX VEX/VDR and CSAF 2.x documents in `vulnerabilities/` say which component is affected, matched by purl, offline. A vulnerability that affects or may affect a component needs a threat listing it (`vulnerabilities`), otherwise error `vulnerability-untreated`. GUI view with upload and "create threat", command `threatwright vulnerabilities`, report section `vulnerabilities` ([docs/sbom.md](docs/sbom.md), ADR-0016).
- **Approvals with evidence.** Decisions get `role` and `date`; approvers in the method may be named by person or role. Warning `acceptance-undocumented`. Report section `approvals` with the Git commit, tag and uncommitted changes the document was built from.
- **Evidence on measures.** `evidence_refs`: https links or files under `evidence/`, uploaded in the measure form. Error `evidence-missing`, warning `implemented-without-evidence`.
- **Support period and review.** `support_until` and `next_review` in `threatwright.yaml`, editable in the settings with the lifecycle phase; warnings `support-period-missing`, `support-period-ended`, `review-overdue`; shown on the cover page.
- **Change evidence in the GUI.** View comparing the editor state with a release tag or the last commit, with Markdown download.

### Working with the tool

- **Diagram connections.** Connections keep the node sides you choose and can have bend points: drag an end to another side or element, add, move and remove bend points, reset the route. Auto layout keeps ELK's orthogonal routes, so lines go around elements instead of behind them; parallel connections are spread apart; the selected connection is highlighted. The SVG export follows the same routes.
- **Example projects.** `threatwright init --example` and "With example model" in the GUI create a small example of the product type.
- **Archive.** Projects can be archived on the start page; they then only show up in the search and can be deleted for good after a confirmation.
- **English documentation.** Quick start and tutorial in `docs/en/`.
