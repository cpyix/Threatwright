<script lang="ts">
  import {
    Background,
    ConnectionMode,
    Controls,
    MarkerType,
    Panel,
    type Connection,
    SvelteFlow,
    useSvelteFlow,
    type Edge,
    type Node,
  } from '@xyflow/svelte'
  import AlignCenterHorizontal from '@lucide/svelte/icons/align-center-horizontal'
  import AlignCenterVertical from '@lucide/svelte/icons/align-center-vertical'
  import AlignEndHorizontal from '@lucide/svelte/icons/align-end-horizontal'
  import AlignEndVertical from '@lucide/svelte/icons/align-end-vertical'
  import AlignHorizontalDistributeCenter from '@lucide/svelte/icons/align-horizontal-distribute-center'
  import AlignStartHorizontal from '@lucide/svelte/icons/align-start-horizontal'
  import AlignStartVertical from '@lucide/svelte/icons/align-start-vertical'
  import AlignVerticalDistributeCenter from '@lucide/svelte/icons/align-vertical-distribute-center'
  import { untrack } from 'svelte'
  import { facing, type Side } from './route'
  import { api } from '../../api'
  import { tr, type Key } from '../../i18n'
  import { app } from '../../state.svelte'
  import type { EdgeLayout, ElementType, ModelPayload, Note, Obj } from '../../types'
  import Legend from './Legend.svelte'
  import ElementNode from './ElementNode.svelte'
  import FlowEdge from './FlowEdge.svelte'
  import NoteNode from './NoteNode.svelte'
  import ZoneNode from './ZoneNode.svelte'

  let {
    flowType,
    configuration,
    flowFilter = [],
    search = '',
    snap = false,
    types,
    onselect,
    onsearchhits = () => {},
  }: {
    flowType: string
    configuration: string[] // selected variants; empty = all
    flowFilter?: string[] // selected connection types ('' = untyped); empty = all
    search?: string
    snap?: boolean
    types: ElementType[]
    onselect: (collection: 'elements' | 'flows', id: string | null) => void
    onsearchhits?: (count: number) => void
  } = $props()

  const W = 170
  const H = 64
  const PAD = 24
  const nodeTypes = { element: ElementNode, zone: ZoneNode, note: NoteNode }
  const edgeTypes = { flow: FlowEdge }
  const { screenToFlowPosition, fitView } = useSvelteFlow()

  let nodes = $state.raw<Node[]>([])
  let edges = $state.raw<Edge[]>([])

  // objects without variants belong to every variant
  const inVariant = (configs: string[] | undefined) =>
    !configuration.length || !configs?.length || configs.some((c) => configuration.includes(c))
  const flowShown = (f: Obj) => inVariant(f.configurations) && (!flowFilter.length || flowFilter.includes(f.protocol ?? ''))

  /** Elements left after both filters: with a type filter only those its connections touch. */
  function shownElements(): Set<string> {
    const touched = new Set(app.objects('flows').filter(flowShown).flatMap((f) => [f.source, f.target]))
    return new Set(
      app
        .objects('elements')
        .filter((e) => inVariant(e.configurations) && (!flowFilter.length || touched.has(e.id)))
        .map((e) => e.id),
    )
  }

  const matches = (q: string, ...fields: (string | null | undefined)[]) =>
    !q || fields.some((f) => f?.toLowerCase().includes(q))

  /** Stored routes (sides, bend points) of the data flows; layout data, never model content. */
  const routes = (): Record<string, EdgeLayout> => structuredClone($state.snapshot(app.model?.layout.edges ?? {}))

  function zoneNodes(positions: Map<string, { x: number; y: number }>, shown: Set<string>): Node[] {
    const out: Node[] = []
    for (const zone of app.model?.meta.zones ?? []) {
      const members = app
        .objects('elements')
        .filter((e) => e.zone === zone.id && positions.has(e.id) && shown.has(e.id))
        .map((e) => positions.get(e.id)!)
      if (!members.length) continue
      const x0 = Math.min(...members.map((p) => p.x)) - PAD
      const y0 = Math.min(...members.map((p) => p.y)) - PAD - 14
      const x1 = Math.max(...members.map((p) => p.x)) + W + PAD
      const y1 = Math.max(...members.map((p) => p.y)) + H + PAD
      out.push({
        id: `zone:${zone.id}`,
        type: 'zone',
        position: { x: x0, y: y0 },
        data: { id: zone.id, title: zone.title, width: x1 - x0, height: y1 - y0 },
        draggable: false,
        selectable: false,
        connectable: false,
        zIndex: -1,
      })
    }
    return out
  }

  function build() {
    const model = app.model
    if (!model) return
    const positions = new Map<string, { x: number; y: number }>()
    let free = 0
    for (const e of app.objects('elements')) {
      const p = model.layout.nodes[e.id]
      positions.set(e.id, p ? { x: p.x, y: p.y } : { x: 40 + (free % 4) * 250, y: 40 + Math.floor(free++ / 4) * 160 })
    }
    const shown = shownElements()
    const q = search.trim().toLowerCase()
    const hits: string[] = []
    // keep the selection across rebuilds (filter, search, saving the layout)
    const wasSelected = new Set(untrack(() => nodes.filter((n) => n.selected).map((n) => n.id)))
    const icons = new Map(types.map((t) => [t.id, t.icon]))
    const threats = new Map<string, number>()
    for (const t of app.objects('threats')) for (const id of t.targets ?? []) threats.set(id, (threats.get(id) ?? 0) + 1)
    const elementNodes: Node[] = app.objects('elements').map((e) => {
      const hit = matches(q, e.id, e.title)
      if (q && hit && shown.has(e.id)) hits.push(e.id)
      return {
      id: e.id,
      type: 'element',
      position: positions.get(e.id)!,
      selected: wasSelected.has(e.id),
      class: hit ? '' : 'dimmed',
      data: {
        id: e.id,
        title: e.title,
        kind: e.kind,
        risk: model.max_risks[e.id] ?? 0,
        icon: icons.get(/element\/([^@]+)@/.exec(e.library_ref ?? '')?.[1] ?? '') ?? null,
        threats: threats.get(e.id) ?? 0,
      },
      hidden: !shown.has(e.id),
      }
    })
    const noteNodes: Node[] = Object.entries(model.layout.notes ?? {}).map(([id, n]) => {
      const hit = matches(q, n.text)
      if (q && hit) hits.push(id)
      return {
        id,
        type: 'note',
        position: { x: n.x, y: n.y },
        selected: wasSelected.has(id),
        class: hit ? '' : 'dimmed',
        data: { id, text: n.text, editing: id === editNote, onchange: (text: string) => setNoteText(id, text) },
      }
    })
    nodes = [...zoneNodes(positions, shown), ...elementNodes, ...noteNodes]
    const zoneOf = new Map(app.objects('elements').map((e) => [e.id, e.zone]))
    const stored = model.layout.edges ?? {}
    // parallel connections without an own route get spread apart instead of drawn on top
    const pairKey = (f: Obj) => [f.source, f.target].sort().join('|')
    const parallel = new Map<string, string[]>()
    for (const f of app.objects('flows'))
      if (!stored[f.id]?.points?.length) parallel.set(pairKey(f), [...(parallel.get(pairKey(f)) ?? []), f.id])
    const wasSelectedEdge = new Set(untrack(() => edges.filter((e) => e.selected).map((e) => e.id)))
    edges = app.objects('flows').map((f) => {
      // anchors follow the geometry unless the user chose a side, so a connection never
      // jumps to a far side of the box by itself
      const [autoSource, autoTarget] =
        positions.has(f.source) && positions.has(f.target)
          ? facing(positions.get(f.source)!, positions.get(f.target)!, W, H)
          : (['right', 'left'] as const)
      const route = stored[f.id] ?? {}
      const group = parallel.get(pairKey(f)) ?? [f.id]
      const shift = (group.indexOf(f.id) - (group.length - 1) / 2) * 18
      const hit = matches(q, f.id, f.title, f.protocol)
      if (q && hit && flowShown(f)) hits.push(f.source, f.target)
      return {
      id: f.id,
      source: f.source,
      target: f.target,
      sourceHandle: route.source_side ?? autoSource,
      targetHandle: route.target_side ?? autoTarget,
      type: 'flow',
      selected: wasSelectedEdge.has(f.id),
      data: { points: route.points ?? [], shift: group.length > 1 ? shift : 0, onpoints: setPoints },
      label: f.title,
      markerEnd: { type: MarkerType.ArrowClosed },
      markerStart: f.bidirectional ? { type: MarkerType.ArrowClosed } : undefined,
      hidden: !flowShown(f),
      class: [
        (model.max_risks[f.id] ?? 0) >= 4 ? 'high-risk' : '',
        zoneOf.get(f.source) !== zoneOf.get(f.target) ? 'cross-zone' : '',
        hit ? '' : 'dimmed',
      ].join(' '),
      }
    })
    searchHits = [...new Set(hits)]
    onsearchhits(q ? searchHits.length : 0)
  }

  let searchHits: string[] = []
  let editNote: string | null = null // a new note opens in edit mode

  /** Zoom to the search hits (elements, notes, ends of matching connections). */
  export function showHits() {
    if (searchHits.length) fitView({ nodes: searchHits.map((id) => ({ id })), maxZoom: 1, duration: 300 })
  }

  /** Smallest zone box containing the point; zone boxes may nest or overlap. */
  function zoneAt(x: number, y: number): string | null {
    let best: { id: string; area: number } | null = null
    for (const n of nodes) {
      if (n.type !== 'zone') continue
      const { width, height } = n.data as { width: number; height: number }
      const inside = x >= n.position.x && x <= n.position.x + width && y >= n.position.y && y <= n.position.y + height
      if (inside && (!best || width * height < best.area)) best = { id: n.id.slice('zone:'.length), area: width * height }
    }
    return best?.id ?? null
  }

  async function ondragstop(dragged: Node[]) {
    // hit-test against the boxes as drawn before the drag; saving the layout redraws them
    const moves = dragged
      .filter((n) => n.type === 'element')
      .map((n) => ({ element: app.objects('elements').find((e) => e.id === n.id), zone: zoneAt(n.position.x + W / 2, n.position.y + H / 2) }))
    await saveLayout(currentLayout())
    // ponytail: leaving a zone into empty space keeps the zone (its box grows); reassigning needs a target zone
    for (const { element, zone } of moves) {
      if (!element || !zone || zone === element.zone) continue
      const r = await api<{ model: ModelPayload }>('PUT', `/models/${app.modelName}/elements/${element.id}`, {
        ...$state.snapshot(element),
        zone,
      })
      await app.afterChange(r.model)
    }
  }

  $effect(() => {
    void app.model
    void configuration
    void flowFilter
    void search
    void types
    build()
  })

  function currentLayout() {
    const out: Record<string, { x: number; y: number }> = {}
    for (const n of nodes) {
      if (n.type === 'element') out[n.id] = { x: Math.round(n.position.x), y: Math.round(n.position.y) }
    }
    return out
  }

  function currentNotes() {
    const out: Record<string, Note> = {}
    for (const n of nodes) {
      if (n.type === 'note') out[n.id] = { x: Math.round(n.position.x), y: Math.round(n.position.y), text: (n.data as { text: string }).text }
    }
    return out
  }

  async function saveLayout(
    layout: Record<string, { x: number; y: number }>,
    notes = currentNotes(),
    edgeRoutes = routes(),
  ) {
    await api('PUT', `/models/${app.modelName}/layout`, { nodes: layout, edges: edgeRoutes, notes })
    if (app.model) app.model.layout = { nodes: layout, edges: edgeRoutes, notes }
    await app.refreshProject()
    build()
  }

  /** Bend points of one connection, from dragging, adding or removing them on the canvas. */
  async function setPoints(id: string, points: { x: number; y: number }[]) {
    const all = routes()
    const current = edges.find((e) => e.id === id)
    // keep the sides the line is drawn with now, so adding a point does not flip them
    all[id] = {
      source_side: (current?.sourceHandle as EdgeLayout['source_side']) ?? null,
      target_side: (current?.targetHandle as EdgeLayout['target_side']) ?? null,
      points: points.map((p) => ({ x: Math.round(p.x), y: Math.round(p.y) })),
    }
    await saveLayout(currentLayout(), currentNotes(), all)
  }

  /** Back to the automatic route: sides facing each other, no bend points. */
  export async function resetRoute(id: string) {
    const all = routes()
    delete all[id]
    await saveLayout(currentLayout(), currentNotes(), all)
  }

  const selectedEdge = $derived(edges.find((e) => e.selected && !e.hidden)?.id ?? null)

  /** Dragging an end of a connection: another side of the same element, or another element. */
  async function onreconnect(old: Edge, c: Connection) {
    // the anchor drag may report the ends the other way round
    const swapped = c.source === old.target && c.target === old.source && c.source !== c.target
    const [source, target] = swapped ? [c.target, c.source] : [c.source, c.target]
    const [sourceSide, targetSide] = swapped ? [c.targetHandle, c.sourceHandle] : [c.sourceHandle, c.targetHandle]
    if (source === target) return
    if (source !== old.source || target !== old.target) {
      const flow = app.objects('flows').find((f) => f.id === old.id)
      if (!flow) return
      const r = await api<{ model: ModelPayload }>('PUT', `/models/${app.modelName}/flows/${old.id}`, {
        ...$state.snapshot(flow),
        source,
        target,
      })
      await app.afterChange(r.model)
    }
    const all = routes()
    // the old bend points belonged to the old ends: start over with the new sides
    all[old.id] = { source_side: (sourceSide as EdgeLayout['source_side']) ?? null, target_side: (targetSide as EdgeLayout['target_side']) ?? null, points: [] }
    await saveLayout(currentLayout(), currentNotes(), all)
  }

  async function setNoteText(id: string, text: string) {
    const notes = currentNotes()
    if (text.trim()) notes[id] = { ...notes[id], text }
    else delete notes[id]
    editNote = null
    await saveLayout(currentLayout(), notes)
  }

  export async function addNote() {
    const box = host!.getBoundingClientRect()
    const c = freeSpot(screenToFlowPosition({ x: box.left + box.width / 2, y: box.top + box.height / 2 }))
    const notes = currentNotes()
    let n = Object.keys(notes).length + 1
    while (`N${n}` in notes) n++
    notes[`N${n}`] = { x: Math.round(c.x - W / 2), y: Math.round(c.y - H / 2), text: '' }
    editNote = `N${n}`
    await saveLayout(currentLayout(), notes)
  }

  // --- arrange the selection ---------------------------------------------------------

  const picked = $derived(nodes.filter((n) => n.selected && !n.hidden && (n.type === 'element' || n.type === 'note')))
  const size = (n: Node) => ({ w: n.measured?.width ?? W, h: n.measured?.height ?? H })

  type Arrange = 'left' | 'hcenter' | 'right' | 'top' | 'vcenter' | 'bottom' | 'dist-h' | 'dist-v'

  /** New top-left corner per selected node; distributing keeps the outer two in place. */
  function arranged(how: Arrange): Map<string, { x: number; y: number }> {
    const box = picked.map((n) => ({ id: n.id, x: n.position.x, y: n.position.y, ...size(n) }))
    const minX = Math.min(...box.map((b) => b.x))
    const maxX = Math.max(...box.map((b) => b.x + b.w))
    const minY = Math.min(...box.map((b) => b.y))
    const maxY = Math.max(...box.map((b) => b.y + b.h))
    const out = new Map<string, { x: number; y: number }>()
    const spread = (axis: 'x' | 'y', len: 'w' | 'h') => {
      const sorted = [...box].sort((a, b) => a[axis] - b[axis])
      const span = Math.max(...box.map((b) => b[axis] + b[len])) - sorted[0][axis]
      const gap = (span - sorted.reduce((sum, b) => sum + b[len], 0)) / (sorted.length - 1)
      let at = sorted[0][axis]
      for (const b of sorted) {
        out.set(b.id, axis === 'x' ? { x: at, y: b.y } : { x: b.x, y: at })
        at += b[len] + gap
      }
    }
    if (how === 'dist-h') spread('x', 'w')
    else if (how === 'dist-v') spread('y', 'h')
    else
      for (const b of box) {
        const x = { left: minX, hcenter: (minX + maxX - b.w) / 2, right: maxX - b.w }[how as string] ?? b.x
        const y = { top: minY, vcenter: (minY + maxY - b.h) / 2, bottom: maxY - b.h }[how as string] ?? b.y
        out.set(b.id, { x, y })
      }
    return out
  }

  async function arrange(how: Arrange) {
    const moved = arranged(how)
    nodes = nodes.map((n) => (moved.has(n.id) ? { ...n, position: moved.get(n.id)! } : n))
    await saveLayout(currentLayout())
  }

  const tools: { how: Arrange; label: Key; icon: typeof AlignStartVertical; min: number }[] = [
    { how: 'left', label: 'align_left', icon: AlignStartVertical, min: 2 },
    { how: 'hcenter', label: 'align_hcenter', icon: AlignCenterVertical, min: 2 },
    { how: 'right', label: 'align_right', icon: AlignEndVertical, min: 2 },
    { how: 'top', label: 'align_top', icon: AlignStartHorizontal, min: 2 },
    { how: 'vcenter', label: 'align_vcenter', icon: AlignCenterHorizontal, min: 2 },
    { how: 'bottom', label: 'align_bottom', icon: AlignEndHorizontal, min: 2 },
    { how: 'dist-h', label: 'distribute_h', icon: AlignHorizontalDistributeCenter, min: 3 },
    { how: 'dist-v', label: 'distribute_v', icon: AlignVerticalDistributeCenter, min: 3 },
  ]

  async function onconnect(c: { source: string; target: string }) {
    if (c.source === c.target) return
    const r = await api<{ id: string; model: ModelPayload }>('POST', `/models/${app.modelName}/add/flow`, {
      source: c.source,
      target: c.target,
      type: flowType || null,
    })
    // afterChange sets the model synchronously; select now, before its validation round,
    // so a click the user makes meanwhile is not overridden afterwards
    const done = app.afterChange(r.model)
    onselect('flows', r.id)
    await done
  }

  let host: HTMLDivElement | undefined = $state()

  async function ondrop(event: DragEvent) {
    event.preventDefault()
    const type = event.dataTransfer?.getData('application/x-threatwright-type')
    if (type) await addAt(type, screenToFlowPosition({ x: event.clientX, y: event.clientY }))
  }

  /** Palette click / keyboard: place in the middle of the visible canvas. */
  export async function addElement(type: string) {
    const box = host!.getBoundingClientRect()
    const c = screenToFlowPosition({ x: box.left + box.width / 2, y: box.top + box.height / 2 })
    await addAt(type, freeSpot(c))
  }

  /** Nearest grid cell around `c` whose element-sized box overlaps no element. */
  function freeSpot(c: { x: number; y: number }) {
    const taken = nodes.filter((n) => n.type === 'element' && !n.hidden).map((n) => n.position)
    const free = (x: number, y: number) =>
      taken.every((p) => Math.abs(p.x - (x - W / 2)) >= W + 30 || Math.abs(p.y - (y - H / 2)) >= H + 30)
    for (let ring = 0; ring < 12; ring++)
      for (let dx = -ring; dx <= ring; dx++)
        for (let dy = -ring; dy <= ring; dy++) {
          if (Math.max(Math.abs(dx), Math.abs(dy)) !== ring) continue
          const x = c.x + dx * (W + 40)
          const y = c.y + dy * (H + 40)
          if (free(x, y)) return { x, y }
        }
    return c
  }

  async function addAt(type: string, p: { x: number; y: number }) {
    const r = await api<{ id: string; model: ModelPayload }>('POST', `/models/${app.modelName}/add/element`, {
      type,
      zone: zoneAt(p.x, p.y) ?? undefined,
      x: Math.round(p.x - W / 2),
      y: Math.round(p.y - H / 2),
    })
    const done = app.afterChange(r.model) // see onconnect: select before validation finishes
    onselect('elements', r.id)
    await done
  }

  export async function autoLayout() {
    const { default: ELK } = await import('elkjs/lib/elk.bundled.js') // loaded on demand
    const elk = new ELK()
    const elements = app.objects('elements')
    const leaf = (id: string) => ({ id, width: W, height: H })
    // generous spacing: room for the connection labels and for lines between the boxes
    const spacing = {
      'elk.spacing.nodeNode': '50',
      'elk.layered.spacing.nodeNodeBetweenLayers': '90',
      'elk.spacing.edgeNode': '30',
      'elk.spacing.edgeEdge': '20',
      'elk.layered.spacing.edgeNodeBetweenLayers': '25',
    }
    // Zones become compound nodes so ELK keeps trust boundaries apart; the padding
    // matches the box zoneNodes() draws around the members afterwards.
    const zones = (app.model?.meta.zones ?? [])
      .map((z) => ({
        id: `zone:${z.id}`,
        layoutOptions: { ...spacing, 'elk.padding': `[top=${PAD + 14},left=${PAD},bottom=${PAD},right=${PAD}]` },
        children: elements.filter((e) => e.zone === z.id).map((e) => leaf(e.id)),
      }))
      .filter((z) => z.children.length)
    const zoned = new Set(zones.flatMap((z) => z.children.map((c) => c.id)))
    const graph = await elk.layout({
      id: 'root',
      layoutOptions: {
        ...spacing,
        'elk.algorithm': 'layered',
        'elk.direction': 'RIGHT',
        'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
        'elk.edgeRouting': 'ORTHOGONAL',
        'elk.edgeLabels.inline': 'true',
      },
      children: [...zones, ...elements.filter((e) => !zoned.has(e.id)).map((e) => leaf(e.id))],
      // labels with their size, so ELK keeps space for them between the layers
      edges: app.objects('flows').map((f) => ({
        id: f.id,
        sources: [f.source],
        targets: [f.target],
        labels: [{ text: f.title, width: f.title.length * 6.5 + 12, height: 18 }],
      })),
    })
    const layout: Record<string, { x: number; y: number }> = {}
    const origin = new Map<string, { x: number; y: number }>([['root', { x: 40, y: 40 }]]) // container -> offset
    for (const c of graph.children ?? []) {
      const ox = (c.x ?? 0) + 40
      const oy = (c.y ?? 0) + 40
      origin.set(c.id, { x: ox, y: oy })
      if (!c.children?.length) layout[c.id] = { x: Math.round(ox), y: Math.round(oy) }
      for (const g of c.children ?? []) layout[g.id] = { x: Math.round(ox + (g.x ?? 0)), y: Math.round(oy + (g.y ?? 0)) }
    }
    await saveLayout(layout, currentNotes(), elkRoutes(graph.edges ?? [], layout, origin))
    fitView({ maxZoom: 1 })
  }

  type ElkEdge = {
    id: string
    container?: string
    sections?: { startPoint: { x: number; y: number }; endPoint: { x: number; y: number }; bendPoints?: { x: number; y: number }[] }[]
  }

  /** ELK's orthogonal routes as stored routes: the sides it attached to and its bend points. */
  function elkRoutes(
    elkEdges: ElkEdge[],
    layout: Record<string, { x: number; y: number }>,
    origin: Map<string, { x: number; y: number }>,
  ): Record<string, EdgeLayout> {
    const out: Record<string, EdgeLayout> = {}
    const sideOf = (p: { x: number; y: number }, box: { x: number; y: number }): Side => {
      const d = { left: Math.abs(p.x - box.x), right: Math.abs(p.x - box.x - W), top: Math.abs(p.y - box.y), bottom: Math.abs(p.y - box.y - H) }
      return (Object.keys(d) as Side[]).reduce((a, b) => (d[b] < d[a] ? b : a))
    }
    for (const e of elkEdges) {
      const flow = app.objects('flows').find((f) => f.id === e.id)
      const s = e.sections?.[0]
      if (!flow || !s || !layout[flow.source] || !layout[flow.target]) continue
      const o = origin.get(e.container ?? 'root') ?? origin.get('root')!
      const abs = (p: { x: number; y: number }) => ({ x: Math.round(p.x + o.x), y: Math.round(p.y + o.y) })
      const src = layout[flow.source]
      const dst = layout[flow.target]
      const sourceSide = sideOf(abs(s.startPoint), src)
      const targetSide = sideOf(abs(s.endPoint), dst)
      const points = (s.bendPoints ?? []).map(abs)
      // our anchors sit in the middle of a side; move the first and last bend onto that line
      const mid = (box: { x: number; y: number }, side: Side) =>
        side === 'left' || side === 'right' ? { axis: 'y' as const, v: box.y + H / 2 } : { axis: 'x' as const, v: box.x + W / 2 }
      if (points.length) {
        const first = mid(src, sourceSide)
        points[0] = { ...points[0], [first.axis]: first.v }
        const last = mid(dst, targetSide)
        points[points.length - 1] = { ...points[points.length - 1], [last.axis]: last.v }
      }
      out[e.id] = { source_side: sourceSide, target_side: targetSide, points }
    }
    return out
  }
</script>

<div class="canvas" role="application" bind:this={host} ondragover={(e) => e.preventDefault()} {ondrop}>
  <SvelteFlow
    bind:nodes
    bind:edges
    {nodeTypes}
    {edgeTypes}
    {onreconnect}
    elevateEdgesOnSelect
    connectionMode={ConnectionMode.Loose}
    colorMode="system"
    deleteKey={null}
    fitView
    fitViewOptions={{ maxZoom: 1 }}
    snapGrid={snap ? [10, 10] : undefined}
    onnodedragstop={({ nodes: dragged }) => ondragstop(dragged)}
    onselectiondragstop={(_, dragged) => ondragstop(dragged)}
    onnodeclick={({ node, event }) =>
      node.type === 'element' && !(event.shiftKey || event.ctrlKey || event.metaKey) && onselect('elements', node.id)}
    onedgeclick={({ edge }) => onselect('flows', edge.id)}
    onpaneclick={() => onselect('elements', null)}
    {onconnect}
  >
    <Background />
    <Controls />
    <Legend />
    {#if selectedEdge}
      <Panel position="bottom-center">
        <div class="arrange" role="toolbar" aria-label={tr(app.lang, 'route')} data-testid="route-tools">
          <span class="count">{tr(app.lang, 'route_help')}</span>
          <button type="button" class="text" onclick={() => resetRoute(selectedEdge!)} data-testid="route-reset">{tr(app.lang, 'route_reset')}</button>
        </div>
      </Panel>
    {/if}
    {#if picked.length >= 2}
      <Panel position="top-center">
        <div class="arrange" role="toolbar" aria-label={tr(app.lang, 'arrange')} data-testid="arrange">
          <span class="count">{picked.length} {tr(app.lang, 'selected_count')}</span>
          {#each tools as t (t.how)}
            {@const Icon = t.icon}
            <button
              type="button"
              disabled={picked.length < t.min}
              onclick={() => arrange(t.how)}
              title={tr(app.lang, t.label)}
              aria-label={tr(app.lang, t.label)}
              data-testid="arrange-{t.how}"
            >
              <Icon size={16} aria-hidden="true" />
            </button>
          {/each}
        </div>
      </Panel>
    {/if}
  </SvelteFlow>
</div>

<style>
  .canvas {
    height: 100%;
    min-height: 30rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  /* the selected connection stands out, so it is clear where it goes */
  .canvas :global(.svelte-flow__edge.selected .svelte-flow__edge-path),
  .canvas :global(.svelte-flow__edge:hover .svelte-flow__edge-path) {
    stroke: var(--accent);
    stroke-width: 3px;
  }
  .arrange button.text {
    width: auto;
    white-space: nowrap;
    padding: 0 8px;
    border-color: var(--border);
    font-size: 12px;
  }
  .canvas :global(.svelte-flow__edge.high-risk path) {
    stroke: var(--error);
    stroke-width: 2px;
  }
  /* crosses a trust boundary */
  .canvas :global(.svelte-flow__edge.cross-zone path) {
    stroke-dasharray: 7 4;
    stroke-width: 2px;
  }
  /* not a search hit */
  .canvas :global(.svelte-flow__node.dimmed),
  .canvas :global(.svelte-flow__edge.dimmed) {
    opacity: 0.2;
  }
  .arrange {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 3px 6px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 2px 8px rgb(0 0 0 / 0.12);
  }
  .arrange .count {
    white-space: nowrap;
    font-size: 12px;
    color: var(--muted);
    margin-right: 4px;
  }
  .arrange button {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    padding: 0;
    border: 1px solid transparent;
    border-radius: var(--radius);
    background: none;
    color: var(--text);
    cursor: pointer;
  }
  .arrange button:hover:not(:disabled) {
    border-color: var(--border);
    background: var(--surface-2);
  }
  .arrange button:disabled {
    opacity: 0.4;
    cursor: default;
  }
  .canvas :global(.svelte-flow__edge-label) {
    background: var(--surface);
    color: var(--text);
    font-size: 11px;
  }
  /* xyflow's own controls and labels in the app's colours (light and dark) */
  .canvas :global(.svelte-flow) {
    --xy-background-color: var(--surface);
    --xy-controls-button-background-color: var(--surface);
    --xy-controls-button-background-color-hover: var(--surface-2);
    --xy-controls-button-color: var(--text);
    --xy-controls-button-color-hover: var(--text);
    --xy-controls-button-border-color: var(--border);
    --xy-edge-label-background-color: var(--surface);
    --xy-edge-label-color: var(--text);
  }
</style>
