# ADR-0007: No network access at runtime

Status: accepted

## Context
A threat model is a list of weaknesses with attack paths. Confidentiality is non-negotiable.

## Decision
- No telemetry, CDNs, web fonts, external renderers, or automatic update checks. All JS/CSS/fonts bundled.
- Server binds `127.0.0.1` only (by default; see ADR-0013 for self-hosting); custom header against CSRF; CSP `default-src 'self'`.
- Tests: a pytest fixture blocks `socket.connect` to non-loopback addresses for the whole suite; Playwright E2E runs with all non-localhost requests aborted and fails on any attempt.

## Consequences
- LibreOffice (PDF) is detected locally and optional; nothing is downloaded on demand.
