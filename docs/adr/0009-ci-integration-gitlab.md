# ADR-0009: CI integration, GitLab first

Status: accepted

## Context
Manufacturers keep threat models in GitLab repos and want documents rendered by the pipeline, not on a laptop. Users without CI knowledge must be able to set this up.

## Decision
- A container image (`threatwright` CLI + LibreOffice for PDF, no GUI deps) is the CI runtime.
- Shipped templates: `ci/gitlab-ci.yml` (primary) and `ci/github-actions.yml`:
  - every MR: `threatwright validate --strict --format junit` → MR test report;
  - default branch and tags: `threatwright build` for all configured templates → job artifacts; on tags additionally `threatwright diff <previous-tag> <tag>` as change evidence.
- The UI (Settings → CI) shows the template **pre-filled for the open project** (models, templates, formats, image tag matching the running version) with a copy button and a "write to `.gitlab-ci.yml`" action (explicit, never automatic). The same text comes from `threatwright ci gitlab` on the CLI.
- The template is a Jinja file in the package, rendered by core code, so UI and CLI output are identical.

## Consequences
- Image tags follow the tool version; templates pin the exact tag for reproducible documents.
- CI is the reference: what the GUI validates, the pipeline validates identically (principle 7).
