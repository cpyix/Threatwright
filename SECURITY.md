# Security policy

Threatwright handles threat models, i.e. lists of weaknesses of your products. We treat
vulnerabilities in the tool itself accordingly.

## Reporting a vulnerability

Report privately via **GitHub private vulnerability reporting**: repository tab *Security* →
*Report a vulnerability*. Please do **not** open a public issue, pull request or discussion.

Helpful content: affected version (`threatwright --version`), operating system, how the tool
was installed (pip, portable build, container image), steps to reproduce or a proof of
concept, and the impact you expect. Do not include real threat models or customer data;
reduce the case to placeholder content.

## What happens next

| Step | Target |
|---|---|
| Acknowledgement of your report | 5 working days |
| First assessment (accepted / not a vulnerability / need more information) | 10 working days |
| Fix or mitigation for high and critical issues | 90 days after acknowledgement |

This is a volunteer-maintained project; the targets are commitments to try, not contractual
service levels. We keep you informed about progress and agree on a disclosure date with you.

## Coordinated disclosure

- We fix in private (GitHub security advisory with a temporary private fork), then release.
- The advisory is published together with the fixed release, with a CVE requested through
  GitHub where applicable, and credits the reporter unless you prefer to stay anonymous.
- Default embargo is 90 days from acknowledgement; earlier if a fix is released, later only
  by mutual agreement. If a vulnerability is actively exploited, we publish as soon as a
  mitigation is available.
- Under the EU Cyber Resilience Act, manufacturers that ship Threatwright inside their own
  products have their own reporting obligations; the advisory gives them what they need.

## Supported versions

Only the latest released minor version receives security fixes while the project is
pre-1.0. Older versions: update (see the release notes for migration hints).

| Version | Supported |
|---|---|
| latest 0.x release | yes |
| older | no |

## Scope

In scope: the Python package, the local web GUI and its API, the portable builds, the
container image and the CI templates in `ci/`. Notable areas: path traversal and zip-slip on
import and export, XML/YAML parsing of untrusted files, template sandbox escapes
(document templates are untrusted code), the local server (binds 127.0.0.1, CSRF header check, Basic Auth by default in server mode,
CSP), and any outbound network access (the tool must make none).

Out of scope: vulnerabilities in your own document templates or models, and findings that
require an attacker who already controls the local user account.

## Verifying releases

Release assets come with `SHA256SUMS`, a Sigstore bundle for it, CycloneDX SBOMs and GitHub
build provenance:

```
gh attestation verify <file> --repo <owner>/threatwright
cosign verify-blob SHA256SUMS --bundle SHA256SUMS.sigstore.json \
  --certificate-identity-regexp 'https://github.com/<owner>/threatwright/.github/workflows/release.yml@refs/tags/v.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
sha256sum -c SHA256SUMS
```
