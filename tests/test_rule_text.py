"""Every documented rule code has a GUI explanation in both languages."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rule_codes_have_gui_text() -> None:
    documented = set(
        re.findall(
            r"^\| `([a-z0-9-]+)` \|", (ROOT / "docs/pruefregeln.md").read_text("utf-8"), re.M
        )
    )
    ts = (ROOT / "app/src/rule-text.ts").read_text("utf-8")
    de, en = ts.split("\n  en: {")
    keys = lambda block: set(re.findall(r"^\s+'?([a-z0-9-]+)'?: ", block, re.M))  # noqa: E731
    assert documented and documented <= keys(de) and documented <= keys(en)
