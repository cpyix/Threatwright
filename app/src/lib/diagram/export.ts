// The diagram exactly as the canvas draws it, as a plain SVG: boxes, lines, icons and text
// are read from the rendered page, so the export never drifts from the view. No HTML inside
// (foreignObject), so Word, PowerPoint and Inkscape show it as well as browsers.

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const visible = (c: string) => c !== 'transparent' && !/rgba\(.*,\s*0\)$/.test(c)
// buttons, connection handles and route anchors are tools, not part of the picture
const SKIP = 'button, textarea, .svelte-flow__handle, .end-anchor, .bend-label'

export function canvasSvg(root: HTMLElement): string {
  const vp = root.querySelector<HTMLElement>('.svelte-flow__viewport')!
  const zoom = new DOMMatrix(getComputedStyle(vp).transform).a || 1
  const o = vp.getBoundingClientRect()
  const out: string[] = []
  const zoneParts: string[] = []
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity
  const grow = (x: number, y: number, w: number, h: number) => {
    x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x + w); y1 = Math.max(y1, y + h)
  }
  const box = (r: DOMRect) => ({ x: (r.left - o.left) / zoom, y: (r.top - o.top) / zoom, w: r.width / zoom, h: r.height / zoom })
  const n = (v: number) => +v.toFixed(1)

  // arrow heads
  const defs = [...root.querySelectorAll('.svelte-flow__marker marker')].map((m) => {
    const c = m.cloneNode(true) as Element
    ;[...m.children].forEach((child, i) => {
      const cs = getComputedStyle(child)
      c.children[i].setAttribute('style', `stroke:${cs.stroke};fill:${cs.fill};stroke-width:${cs.strokeWidth}`)
    })
    return c.outerHTML
  })

  // lines: already in canvas coordinates
  for (const p of root.querySelectorAll<SVGPathElement>('.svelte-flow__edge path.svelte-flow__edge-path')) {
    const cs = getComputedStyle(p)
    const g = p.closest('.svelte-flow__edge')!
    const b = p.getBBox()
    grow(b.x - 10, b.y - 10, b.width + 20, b.height + 20)
    const marks = ['marker-start', 'marker-end'].map((m) => (p.getAttribute(m) ? ` ${m}="${esc(p.getAttribute(m)!)}"` : '')).join('')
    out.push(
      `<path d="${p.getAttribute('d')}" fill="none" stroke="${cs.stroke}" stroke-width="${parseFloat(cs.strokeWidth)}"` +
        (cs.strokeDasharray !== 'none' ? ` stroke-dasharray="${cs.strokeDasharray.replace(/px/g, '')}"` : '') +
        ` opacity="${getComputedStyle(g).opacity}"${marks}/>`,
    )
  }

  // boxes, icons and text: zones go behind the lines, line labels and elements in front
  for (const sel of ['.svelte-flow__edge-labels', '.svelte-flow__nodes']) {
    const layer = root.querySelector<HTMLElement>(sel)
    if (layer) walk(layer, 1)
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${n(x0 - 20)} ${n(y0 - 20)} ${n(x1 - x0 + 40)} ${n(y1 - y0 + 40)}" width="${n(x1 - x0 + 40)}" height="${n(y1 - y0 + 40)}">` +
    `<defs>${defs.join('')}</defs>` +
    `<rect x="${n(x0 - 20)}" y="${n(y0 - 20)}" width="100%" height="100%" fill="${getComputedStyle(root.querySelector('.svelte-flow')!).backgroundColor}"/>` +
    zoneParts.join('') + out.join('') + '</svg>'

  function walk(el: HTMLElement, alpha: number) {
    if (el.matches(SKIP)) return
    const cs = getComputedStyle(el)
    if (cs.display === 'none' || cs.visibility === 'hidden') return
    alpha *= +cs.opacity
    const r = box(el.getBoundingClientRect())
    const sink = el.closest('.svelte-flow__node-zone') ? zoneParts : out
    const op = alpha < 1 ? ` opacity="${alpha}"` : ''
    // only what is drawn counts for the size: layer containers span the whole canvas
    if (r.w && r.h && visible(cs.backgroundColor)) {
      grow(r.x, r.y, r.w, r.h)
      sink.push(`<rect x="${n(r.x)}" y="${n(r.y)}" width="${n(r.w)}" height="${n(r.h)}" rx="${parseFloat(cs.borderTopLeftRadius) || 0}" fill="${cs.backgroundColor}"${op}/>`)
    }
    if (r.w && r.h) border(cs, r, op, sink)
    for (const child of el.childNodes) {
      if (child instanceof HTMLElement) walk(child, alpha)
      else if (child instanceof SVGSVGElement) {
        const b = box(child.getBoundingClientRect())
        grow(b.x, b.y, b.w, b.h)
        const c =child.cloneNode(true) as SVGSVGElement
        c.removeAttribute('class')
        for (const [k, v] of Object.entries({ x: b.x, y: b.y, width: b.w, height: b.h })) c.setAttribute(k, String(n(v)))
        c.setAttribute('color', getComputedStyle(child).color) // lucide draws in currentColor
        sink.push(alpha < 1 ? `<g${op}>${c.outerHTML}</g>` : c.outerHTML)
      } else if (child.nodeType === Node.TEXT_NODE && child.textContent!.trim()) text(child as Text, cs, el, op, sink)
    }
  }

  function border(cs: CSSStyleDeclaration, r: { x: number; y: number; w: number; h: number }, op: string, sink: string[]) {
    const sides = (['Top', 'Right', 'Bottom', 'Left'] as const).map((s) => ({
      w: cs[`border${s}Style`] === 'none' ? 0 : parseFloat(cs[`border${s}Width`]),
      color: cs[`border${s}Color`],
      dash: cs[`border${s}Style`] === 'dashed',
    }))
    if (sides.some((s) => s.w)) grow(r.x, r.y, r.w, r.h)
    const dash = (s: { w: number; dash: boolean }) => (s.dash ? ` stroke-dasharray="${3 * s.w} ${2 * s.w}"` : '')
    if (sides.every((s) => s.w && s.w === sides[0].w && s.color === sides[0].color)) {
      const s = sides[0]
      sink.push(
        `<rect x="${n(r.x + s.w / 2)}" y="${n(r.y + s.w / 2)}" width="${n(r.w - s.w)}" height="${n(r.h - s.w)}" rx="${parseFloat(cs.borderTopLeftRadius) || 0}" fill="none" stroke="${s.color}" stroke-width="${s.w}"${dash(s)}${op}/>`,
      )
      return
    }
    const lines = [
      [r.x, r.y, r.x + r.w, r.y],
      [r.x + r.w, r.y, r.x + r.w, r.y + r.h],
      [r.x, r.y + r.h, r.x + r.w, r.y + r.h],
      [r.x, r.y, r.x, r.y + r.h],
    ]
    sides.forEach((s, i) => {
      if (!s.w) return
      const [a, b, c, d] = lines[i].map(n)
      sink.push(`<line x1="${a}" y1="${b}" x2="${c}" y2="${d}" stroke="${s.color}" stroke-width="${s.w}"${dash(s)}${op}/>`)
    })
  }

  /** One <text> per line as laid out on the page; words cut off by the box end in "…". */
  function text(t: Text, cs: CSSStyleDeclaration, el: HTMLElement, op: string, sink: string[]) {
    const clip = box(el.getBoundingClientRect())
    const range = document.createRange()
    const lines = new Map<number, { x: number; y: number; h: number; words: string[] }>()
    let cut = false
    for (const m of t.textContent!.matchAll(/\S+/g)) {
      range.setStart(t, m.index!)
      range.setEnd(t, m.index! + m[0].length)
      const rects = range.getClientRects()
      if (!rects.length) continue
      const w = box(rects[0])
      if (w.y + w.h > clip.y + clip.h + 1 || w.x + w.w > clip.x + clip.w + 1) {
        cut = true
        continue
      }
      const key = Math.round(w.y)
      const line = lines.get(key) ?? { x: w.x, y: w.y, h: w.h, words: [] }
      line.words.push(m[0])
      lines.set(key, line)
    }
    const all = [...lines.values()]
    if (cut && all.length) all[all.length - 1].words.push('…')
    const size = parseFloat(cs.fontSize)
    const font = `font-family="${esc(cs.fontFamily)}" font-size="${size}" font-weight="${cs.fontWeight}" fill="${cs.color}"`
    for (const l of all) {
      grow(l.x, l.y, 0, l.h)
      sink.push(`<text x="${n(l.x)}" y="${n(l.y + l.h / 2 + size * 0.35)}" ${font}${op}>${esc(l.words.join(' '))}</text>`)
    }
  }
}
