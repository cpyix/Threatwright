# ADR-0013: Self-hosted GUI in a container or on a server

Status: accepted (amends ADR-0007, realises the option in ADR-0003)

## Context
Teams want to run the GUI on an internal server or in a container instead of on every workstation. Inside a container, a server bound to `127.0.0.1` is not reachable from the host.

## Decision
- `--host`, `--port` and `--allowed-host` (repeatable) on the GUI command. Defaults are unchanged: `127.0.0.1`, random port, only `127.0.0.1`/`localhost` accepted as Host.
- Host names given with `--allowed-host` are accepted on any port, so a TLS reverse proxy or a port mapping works. Every other Host header is still rejected (DNS rebinding).
- Server mode (a non-loopback `--host` or any `--allowed-host`) works in a workspace folder (`--workspace`, default the working directory) holding any number of projects. Every path a client sends (open project, new project, upload, OSCAL import) is confined to it. The native folder dialog and "open build folder", which would act on the server's desktop, are switched off; the start page lists the workspace's projects instead.
- Local projects reach the server as an uploaded `.zip` (at most 50 MB, 200 MB unpacked, 5000 files; symlinks skipped, no path may leave the new project folder; the archive must contain a `threatwright.yaml`). The open project can be downloaded as `.zip` (its saved state, without the local version history), in both modes.
- **Authentication, secure by default.** There is no session token. The local GUI binds to `127.0.0.1` and has no login. Server mode (a non-loopback `--host` or any `--allowed-host`) turns on HTTP Basic Auth by default; it is switched off only explicitly with `--auth none` (for an authenticating proxy, e.g. SSO). Users come from `--users-file` (`name:pbkdf2_sha256$…` lines, `threatwright hash-password`), or `THREATWRIGHT_USER`/`THREATWRIGHT_PASSWORD`; with neither, a password is generated once and stored in `<workspace>/.threatwright/password` (owner-only, the folder ignores itself in Git); it is never logged, because logs often end up in central log systems. Verified credentials are cached in memory so the slow hash runs once per client. Unknown user names are checked against a dummy hash, so timing does not reveal valid names.
- **CSRF.** Every API call needs the header `X-Threatwright`. Browsers do not let other websites send such a header without a CORS preflight, which the server never grants, so a page open in the same browser cannot act on the user's behalf. Together with the Host check (DNS rebinding) this replaces the former session token.
- Basic Auth sends the password with every request; beyond the local machine TLS is required (reverse proxy).
- Other users and programs on the same machine can reach the local GUI; that is accepted for a local tool. Shared machines use server mode with login.
- Still no outgoing network access; ADR-0007 applies otherwise unchanged.

## Consequences
- The server holds one shared session: one open project and one person or coordinated team per instance. Concurrent editors overwrite each other's unsaved state; run one instance per team.
- Projects outside the workspace cannot be opened from the GUI. `--project` must lie inside the workspace.
