# ADR-0008: Public repository hygiene and leak checks

Status: accepted

## Context
The repository is public from the first commit. Leaked secrets, AI-assistant state or customer data cannot be recalled once pushed.

## Decision
- `.gitignore` excludes AI-assistant/tool state (`.claude/`, `CLAUDE*.md`, `.mcp.json`, `graphify-out/`, `.cursor/`, `AGENTS.md`, …), env files, key material, build output.
- `.private/` is the place for non-public notes (customer references, drafts); ignored and forbidden like the above. `docs/` stays public.
- `scripts/check_forbidden_files.py` fails if any such path is tracked (ignore rules do not protect against `git add -f`).
- gitleaks (pinned image) scans the **full history** on every push and PR (`.github/workflows/leakcheck.yml`), same checks as pre-commit hooks (`.pre-commit-config.yaml`).
- Actions pinned by commit SHA; workflow token is read-only.
- The repository is fully generic: no example projects derived from real products or customers. Test fixtures use abstract placeholder content only (Controller, Remote I/O, ...); no real names, findings or logos.

## Consequences
- Deviates from brief §12/§3.1: no bundled sample machine project and no `init --template demo`. `init` offers only empty and TR-standard projects; tutorials use neutral placeholder content.
- Contributors install `pre-commit` to catch leaks before they reach a commit.
- On a positive finding: rotate the secret first, then rewrite history.
