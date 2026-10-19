"""Fail if files that must never be public are tracked in git.

Covers what gitleaks cannot see: AI-assistant state, local tool output and
key material that is not a recognisable token. Runs in CI and pre-commit.
"""

import re
import subprocess
import sys

FORBIDDEN = re.compile(
    r"""(^|/)(
        \.claude/ | CLAUDE(\.local)?\.md$ | \.mcp\.json$ | graphify-out/ |
        \.cursor/ | \.aider | AGENTS\.md$ | \.private/ |
        \.env($|\.(?!example$)) | secrets/ |
        [^/]+\.(pem|key|p12|pfx|kdbx)$
    )""",
    re.VERBOSE | re.IGNORECASE,
)


def main() -> int:
    tracked = (
        subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True)
        .stdout.decode()
        .split("\0")
    )
    hits = [p for p in tracked if p and FORBIDDEN.search(p)]
    for p in hits:
        print(f"forbidden file tracked: {p}", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    assert FORBIDDEN.search("a/.claude/settings.json")
    assert FORBIDDEN.search("CLAUDE.md") and FORBIDDEN.search("x/CLAUDE.local.md")
    assert FORBIDDEN.search(".env.prod") and not FORBIDDEN.search(".env.example")
    assert not FORBIDDEN.search("docs/claude-notes.md")
    assert FORBIDDEN.search(".private/kunde.md")
    sys.exit(main())
