"""Sandboxed Jinja environment and the filters documented in docs/vorlagenreferenz.md.

Templates are untrusted: they only ever run in an ImmutableSandboxedEnvironment
and only see plain data (dicts, lists, strings, numbers, dates).
"""

import datetime
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, FileSystemLoader, StrictUndefined
from jinja2.sandbox import ImmutableSandboxedEnvironment

from threatwright.render.labels import MONTHS, Lang, t

SHARED = Path(__file__).resolve().parents[1] / "templates" / "_shared"


def format_date(value: Any, lang: Lang, style: str = "short") -> str:
    if isinstance(value, str):
        try:
            value = datetime.date.fromisoformat(value)
        except ValueError:
            return str(value)
    if not isinstance(value, datetime.date):
        return "–"
    if style == "iso":
        return value.isoformat()
    if style == "long":
        month = MONTHS[lang].split()[value.month - 1]
        return (
            f"{value.day}. {month} {value.year}"
            if lang == "de"
            else (f"{value.day} {month} {value.year}")
        )
    return value.strftime("%d.%m.%Y") if lang == "de" else value.isoformat()


def sort_by_risk(threats: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Highest risk first, unassessed last, ties by id."""
    return sorted(threats, key=lambda th: (-(th.get("risk") or 0), str(th.get("id"))))


def md_cell(value: Any) -> str:
    """Escape a value for a Markdown table cell."""
    text = "" if value is None else str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def make_filters(
    lang: Lang, risk_levels: dict[int, str], impact_levels: dict[int, str]
) -> dict[str, Callable[..., Any]]:
    def label(levels: dict[int, str]) -> Callable[[Any], str]:
        return lambda v: levels.get(v, "–") if isinstance(v, int) else "–"

    return {
        "t": lambda key: t(str(key), lang),
        "risk_label": label(risk_levels),
        "impact_label": label(impact_levels),
        "stride_names": lambda codes: [t(f"stride.{c}", lang) for c in codes or []],
        "sort_by_risk": sort_by_risk,
        "date": lambda v, style="short": format_date(v, lang, style),
        "yesno": lambda v: "–" if v is None else t("yes" if v else "no", lang),
        "md_cell": md_cell,
    }


def make_env(
    filters: dict[str, Callable[..., Any]],
    search_path: list[Path] | None = None,
    autoescape: bool = False,
    text: bool = True,
) -> ImmutableSandboxedEnvironment:
    """`text=False` keeps Jinja's default whitespace handling (needed by docxtpl)."""
    loader: BaseLoader | None = None
    if search_path is not None:
        loader = FileSystemLoader([*search_path, SHARED], encoding="utf-8")
    env = ImmutableSandboxedEnvironment(
        loader=loader,
        autoescape=autoescape,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=text,
        lstrip_blocks=text,
    )
    env.filters.update(filters)
    env.globals["t"] = filters["t"]
    return env
