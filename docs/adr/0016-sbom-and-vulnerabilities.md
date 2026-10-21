# ADR-0016: SBOMs and vulnerability statements as project files

Status: accepted

## Context
CRA Annex I requires products without known exploitable vulnerabilities (part I 2(a)) and a documented inventory of components with vulnerability handling (part II). Manufacturers already produce SBOMs and vulnerability data with their own tools: SBOM generators, scanners, supplier advisories. Threatwright has to link that data to the threat model without querying any online database (ADR-0007).

## Decision
- **Files, not services.** CycloneDX JSON SBOMs live in `<project>/sbom/`, vulnerability statements (CycloneDX VEX/VDR, CSAF 2.x JSON) in `<project>/vulnerabilities/`. They are versioned in Git with the model. Uploads in the GUI only store a file after it parsed.
- **Element to SBOM.** An element lists its SBOM files (`sbom: [file.json]`); no per-component modelling. A firmware or application element usually has one SBOM.
- **Matching by purl** without qualifiers and subpath, version included. Components without a purl are ignored.
- **State merge.** Per vulnerability and component: not affected > fixed > under investigation > affected, so a manufacturer's VEX settles a scanner finding.
- **Treatment through threats.** A vulnerability that affects (or may affect) a component needs a threat listing its id in `vulnerabilities`. Rule `vulnerability-untreated` is an error: the CRA forbids placing a product with a known exploitable vulnerability on the market. Measures, residual risk and acceptance follow the normal method.
- **Additive fields** (`Element.sbom`, `Threat.vulnerabilities`): no new schema version (ADR-0015).

## Consequences
- No automatic lookup of new CVEs: users refresh the files (e.g. a scanner in CI writing `vulnerabilities/scan.json`). The CI pipeline then fails on new untreated findings.
- SPDX SBOMs are not read yet; convert them to CycloneDX or add a reader when users ask.
- Parsed files are cached by path, size and modification time, because validation runs after every GUI edit.
