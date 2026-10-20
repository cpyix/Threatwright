# ADR-0013: Self-hosted GUI in a container or on a server

Status: accepted (amends ADR-0007, realises the option in ADR-0003)

## Context
Teams want to run the GUI on an internal server or in a container instead of on every workstation. Inside a container, a server bound to `127.0.0.1` is not reachable from the host.

## Decision
- `--host`, `--port` and `--allowed-host` (repeatable) on the GUI command. Defaults are unchanged: `127.0.0.1`, random port, only `127.0.0.1`/`localhost` accepted as Host.
- Host names given with `--allowed-host` are accepted on any port, so a TLS reverse proxy or a port mapping works. Every other Host header is still rejected (DNS rebinding).
- `THREATWRIGHT_TOKEN` (at least 24 characters) fixes the token across restarts; without it a random token is generated per start, as before.
- Server mode (a non-loopback `--host` or any `--allowed-host`) works in a workspace folder (`--workspace`, default the working directory) holding any number of projects. Every path a client sends (open project, new project, upload, OSCAL import) is confined to it. The native folder dialog and "open build folder", which would act on the server's desktop, are switched off; the start page lists the workspace's projects instead.
- Local projects reach the server as an uploaded `.zip` (at most 50 MB, 200 MB unpacked, 5000 files; symlinks skipped, no path may leave the new project folder; the archive must contain a `threatwright.yaml`). The open project can be downloaded as `.zip` (its saved state, without the local version history), in both modes.
- The token remains Threatwright's only authentication; user login is the reverse proxy's job (the README shows Caddy with TLS and HTTP Basic Auth; SSO via e.g. oauth2-proxy works the same). Exposure beyond a single host requires such a proxy. No login of our own: it would need password storage, TLS and session handling that the proxy already does well.
- Still no outgoing network access; ADR-0007 applies otherwise unchanged.

## Consequences
- The server holds one shared session: one open project and one person or coordinated team per instance. Concurrent editors overwrite each other's unsaved state; run one instance per team.
- Projects outside the workspace cannot be opened from the GUI. `--project` must lie inside the workspace.
