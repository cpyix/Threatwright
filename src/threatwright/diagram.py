"""Data flow diagram as standalone SVG (for documents and export).

Pure Python, deterministic, no external renderer (ADR-0007). Positions come
from diagram.layout.yaml; elements without a position are placed on a grid.
Zones are drawn as dashed frames around their member elements.
"""

from html import escape

from threatwright.model.objects import Element, Flow
from threatwright.model.store import SubModel

W, H = 170, 64  # node size
PAD = 24
LINE = 'stroke="#1b1f24" stroke-width="1.5"'
RISK_FILL = {1: "#d7f0dc", 2: "#e9f3c7", 3: "#fbe7b5", 4: "#f8cdb0", 5: "#f3b6b6"}


def positions(sub: SubModel) -> dict[str, tuple[float, float]]:
    pos: dict[str, tuple[float, float]] = {}
    free = 0
    for eid in sorted(sub.objects["elements"]):
        node = sub.layout.nodes.get(eid)
        if node is not None:
            pos[eid] = (node.x, node.y)
        else:
            pos[eid] = (40 + (free % 4) * (W + 80), 40 + (free // 4) * (H + 90))
            free += 1
    return pos


def _shape(e: Element, x: float, y: float, fill: str) -> str:
    style = f'fill="{fill}" stroke="#1b1f24" stroke-width="1.5"'
    if e.kind == "process":
        return f'<rect x="{x}" y="{y}" width="{W}" height="{H}" rx="{H / 2}" {style}/>'
    if e.kind == "datastore":
        return (
            f'<rect x="{x}" y="{y}" width="{W}" height="{H}" fill="{fill}" stroke="none"/>'
            f'<line x1="{x}" y1="{y}" x2="{x + W}" y2="{y}" {LINE}/>'
            f'<line x1="{x}" y1="{y + H}" x2="{x + W}" y2="{y + H}" {LINE}/>'
        )
    if e.kind == "external":
        return f'<rect x="{x}" y="{y}" width="{W}" height="{H}" {style} stroke-width="3"/>'
    return f'<rect x="{x}" y="{y}" width="{W}" height="{H}" rx="6" {style}/>'


def _text(x: float, y: float, text: str, size: int = 12, weight: str = "normal") -> str:
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="middle" font-family="sans-serif">{escape(text)}</text>'
    )


def _short(text: str, n: int = 26) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def render_svg(sub: SubModel, risks: dict[str, int] | None = None) -> str:
    """SVG of the model; `risks` maps element/flow id to its highest risk (colour)."""
    risks = risks or {}
    pos = positions(sub)
    elements = {i: e for i, e in sub.objects["elements"].items() if isinstance(e, Element)}
    parts: list[str] = []

    for zone in sub.meta.zones:
        members = [pos[i] for i, e in elements.items() if e.zone == zone.id]
        if not members:
            continue
        x0 = min(p[0] for p in members) - PAD
        y0 = min(p[1] for p in members) - PAD - 14
        x1 = max(p[0] for p in members) + W + PAD
        y1 = max(p[1] for p in members) + H + PAD
        parts.append(
            f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="none" '
            f'stroke="#555e69" stroke-dasharray="6 4" rx="8"/>'
            f'<text x="{x0 + 8}" y="{y0 + 16}" font-size="12" font-family="sans-serif" '
            f'fill="#555e69">{escape(zone.title)}</text>'
        )

    for fid in sorted(sub.objects["flows"]):
        f = sub.objects["flows"][fid]
        if not isinstance(f, Flow) or f.source not in pos or f.target not in pos:
            continue
        (sx, sy), (tx, ty) = pos[f.source], pos[f.target]
        x1, y1, x2, y2 = sx + W / 2, sy + H / 2, tx + W / 2, ty + H / 2
        colour = "#a4161a" if risks.get(fid, 0) >= 4 else "#1b1f24"
        marker = ' marker-start="url(#arrow)"' if f.bidirectional else ""
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colour}" stroke-width="1.5" '
            f'marker-end="url(#arrow)"{marker}/>'
            + _text((x1 + x2) / 2, (y1 + y2) / 2 - 6, f"{fid} {_short(f.title, 22)}", 11)
        )

    for eid in sorted(elements):
        e = elements[eid]
        x, y = pos[eid]
        parts.append(_shape(e, x, y, RISK_FILL.get(risks.get(eid, 0), "#ffffff")))
        parts.append(_text(x + W / 2, y + 26, eid, 11, "bold"))
        parts.append(_text(x + W / 2, y + 44, _short(e.title)))

    corners = list(pos.values())
    for nid in sorted(sub.layout.notes):
        note = sub.layout.notes[nid]
        lines = note.text.splitlines() or [""]
        nw = max(len(line) for line in lines) * 7 + 16
        nh = len(lines) * 16 + 12
        text = "".join(
            f'<tspan x="{note.x + 8}" dy="{16 if i else 0}">{escape(line)}</tspan>'
            for i, line in enumerate(lines)
        )
        parts.append(
            f'<rect x="{note.x}" y="{note.y}" width="{nw}" height="{nh}" fill="#fff8c5" '
            f'stroke="#d4a72c" rx="4"/>'
            f'<text x="{note.x + 8}" y="{note.y + 20}" font-size="12" font-family="sans-serif" '
            f'fill="#1b1f24">{text}</text>'
        )
        corners.append((note.x + nw - W, note.y + nh - H))

    width = max((p[0] for p in corners), default=0) + W + 2 * PAD + 20
    height = max((p[1] for p in corners), default=0) + H + 2 * PAD + 20
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}">'
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" '
        'markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        'fill="#1b1f24"/></marker></defs>'
        '<rect width="100%" height="100%" fill="#ffffff"/>' + "".join(parts) + "</svg>\n"
    )
