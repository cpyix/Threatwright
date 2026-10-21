"""Data flow diagram as standalone SVG (for documents and export).

Pure Python, deterministic, no external renderer (ADR-0007). Positions come
from diagram.layout.yaml; elements without a position are placed on a grid.
Zones are drawn as dashed frames around their member elements.
"""

from html import escape
from itertools import pairwise

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


Pt = tuple[float, float]
STUB = 16  # a line leaves a node straight for this distance before turning


def facing(a: Pt, b: Pt) -> tuple[str, str]:
    """Sides facing each other: side by side -> right/left, above each other -> bottom/top."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) * H >= abs(dy) * W:
        return ("right", "left") if dx >= 0 else ("left", "right")
    return ("bottom", "top") if dy >= 0 else ("top", "bottom")


def anchor(p: Pt, side: str, out: float = 0) -> Pt:
    x, y = p
    return {
        "top": (x + W / 2, y - out),
        "right": (x + W + out, y + H / 2),
        "bottom": (x + W / 2, y + H + out),
        "left": (x - out, y + H / 2),
    }[side]


def route(sub: SubModel, f: Flow, pos: dict[str, Pt]) -> list[Pt]:
    """Polyline of a flow: stored sides and bend points, right angles in between.

    Same rules as the GUI's FlowEdge (app/src/lib/diagram/route.ts).
    """
    s, t = pos[f.source], pos[f.target]
    layout = sub.layout.edges.get(f.id)
    auto_s, auto_t = facing(s, t)
    s_side = (layout.source_side if layout else None) or auto_s
    t_side = (layout.target_side if layout else None) or auto_t
    via = [(p.x, p.y) for p in layout.points] if layout else []
    if not via:
        return [anchor(s, s_side), anchor(t, t_side)]
    stops = [anchor(s, s_side), anchor(s, s_side, STUB), *via, anchor(t, t_side, STUB)]
    out = [stops[0]]
    for p in stops[1:]:
        c = out[-1]
        if c[0] != p[0] and c[1] != p[1]:
            out.append((p[0], c[1]))  # horizontal first, then vertical
        out.append(p)
    out.append(anchor(t, t_side))
    return out


def _middle(points: list[Pt]) -> Pt:
    """Middle of the longest segment: room for the label."""
    a, b = max(pairwise(points), key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


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
        return (
            f'<rect x="{x}" y="{y}" width="{W}" height="{H}" fill="{fill}"'
            ' stroke="#1b1f24" stroke-width="3"/>'
        )
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
        points = route(sub, f, pos)
        colour = "#a4161a" if risks.get(fid, 0) >= 4 else "#1b1f24"
        marker = ' marker-start="url(#arrow)"' if f.bidirectional else ""
        mx, my = _middle(points)
        path = " ".join(f"{x:g},{y:g}" for x, y in points)
        parts.append(
            f'<polyline points="{path}" fill="none" stroke="{colour}" stroke-width="1.5" '
            f'marker-end="url(#arrow)"{marker}/>'
            + _text(mx, my - 6, f"{fid} {_short(f.title, 22)}", 11)
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
