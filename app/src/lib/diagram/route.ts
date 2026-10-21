// Routes of data flows: right angles between the node sides and stored bend points.
// Same rules as route() in src/threatwright/diagram.py (SVG for documents).

export type Side = 'top' | 'right' | 'bottom' | 'left'
export type Pt = { x: number; y: number }

export const STUB = 16 // a line leaves a node straight for this distance before turning
export const GRID = 10

/** Sides facing each other: side by side -> right/left, above each other -> bottom/top. */
export function facing(a: Pt, b: Pt, w: number, h: number): [Side, Side] {
  const dx = b.x - a.x
  const dy = b.y - a.y
  if (Math.abs(dx) * h >= Math.abs(dy) * w) return dx >= 0 ? ['right', 'left'] : ['left', 'right']
  return dy >= 0 ? ['bottom', 'top'] : ['top', 'bottom']
}

export function stub(p: Pt, side: Side, d = STUB): Pt {
  return {
    top: { x: p.x, y: p.y - d },
    right: { x: p.x + d, y: p.y },
    bottom: { x: p.x, y: p.y + d },
    left: { x: p.x - d, y: p.y },
  }[side]
}

/** Polyline from anchor `a` (leaving on `aSide`) through `via` to anchor `b`, right angles only. */
export function orthogonal(a: Pt, aSide: Side, via: Pt[], b: Pt, bSide: Side): Pt[] {
  const stops = [stub(a, aSide), ...via, stub(b, bSide)]
  const out: Pt[] = [a, stops[0]]
  for (const p of stops.slice(1)) {
    const c = out[out.length - 1]
    if (c.x !== p.x && c.y !== p.y) out.push({ x: p.x, y: c.y }) // horizontal first, then vertical
    out.push(p)
  }
  out.push(b)
  return out
}

/** SVG path with slightly rounded corners. */
export function pathOf(points: Pt[], radius = 6): string {
  let d = `M ${points[0].x} ${points[0].y}`
  for (let i = 1; i < points.length - 1; i++) {
    const [p, c, n] = [points[i - 1], points[i], points[i + 1]]
    const r = Math.min(radius, dist(p, c) / 2, dist(c, n) / 2)
    const a = towards(c, p, r)
    const b = towards(c, n, r)
    d += ` L ${a.x} ${a.y} Q ${c.x} ${c.y} ${b.x} ${b.y}`
  }
  const last = points[points.length - 1]
  return `${d} L ${last.x} ${last.y}`
}

/** Middle of the longest segment: room for the label. */
export function middle(points: Pt[]): Pt {
  let best = { len: -1, at: points[0] }
  for (let i = 1; i < points.length; i++) {
    const len = dist(points[i - 1], points[i])
    if (len > best.len) best = { len, at: { x: (points[i - 1].x + points[i].x) / 2, y: (points[i - 1].y + points[i].y) / 2 } }
  }
  return best.at
}

/** Point at fraction `t` (0..1) of the polyline's length. */
export function along(points: Pt[], t: number): Pt {
  const total = points.slice(1).reduce((s, p, i) => s + dist(points[i], p), 0)
  let left = total * t
  for (let i = 1; i < points.length; i++) {
    const d = dist(points[i - 1], points[i])
    if (left <= d) return towards(points[i - 1], points[i], left)
    left -= d
  }
  return points[points.length - 1]
}

export const snap = (p: Pt): Pt => ({ x: Math.round(p.x / GRID) * GRID, y: Math.round(p.y / GRID) * GRID })

const dist = (a: Pt, b: Pt) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y)

function towards(from: Pt, to: Pt, r: number): Pt {
  const d = dist(from, to) || 1
  return { x: from.x + ((to.x - from.x) / d) * r, y: from.y + ((to.y - from.y) / d) * r }
}
