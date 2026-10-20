# ADR-0013: Self-hosted GUI in a container or on a server

Status: accepted (amends ADR-0007, realises the option in ADR-0003)

## Context
Teams want to run the GUI on an internal server or in a container instead of on every workstation. Inside a container, a server bound to `127.0.0.1` is not reachable from the host.

## Decision
- `--host`, `--port` and `--allowed-host` (repeatable) on the GUI command. Defaults are unchanged: `127.0.0.1`, random port, only `127.0.0.1`/`localhost` accepted as Host.
- Host names given with `--allowed-host` are accepted on any port, so a TLS reverse proxy or a port mapping works. Every other Host header is still rejected (DNS rebinding).
- `THREATWRIGHT_TOKEN` (at least 24 characters) fixes the token across restarts; without it a random token is generated per start, as before.
- Server mode (a non-loopback `--host` or any `--allowed-host`) confines every path a client sends (open project, new project, OSCAL import) to the `--project` folder, or the working directory without it, and switches off the native folder dialog and "open build folder", which would act on the server's desktop.
- The token remains the only authentication. Exposure beyond a single host requires a reverse proxy with TLS and the organisation's own access control (VPN, SSO).
- Still no outgoing network access; ADR-0007 applies otherwise unchanged.

## Consequences
- The server holds one shared session: one person or one coordinated team per instance. Concurrent editors overwrite each other's unsaved state; run one instance per project.
- The project is passed with `--project`; projects elsewhere on the server cannot be opened from the GUI.
