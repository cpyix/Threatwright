<script lang="ts">
  import {
    Background,
    ConnectionMode,
    Controls,
    MarkerType,
    Panel,
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
  import { api } from '../../api'
  import { tr, type Key } from '../../i18n'
  import { app } from '../../state.svelte'
  import type { ElementType, ModelPayload, Note, Obj } from '../../types'
  import Legend from './Legend.svelte'
  import ElementNode from './ElementNode.svelte'
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

  /** Handles facing each other: side by side -> right/left, above each other -> bottom/top. */
  function sides(a: { x: number; y: number }, b: { x: number; y: number }): [string, string] {
    const dx = b.x - a.x
    const dy = b.y - a.y
    if (Math.abs(dx) * H >= Math.abs(dy) * W) return dx >= 0 ? ['right', 'left'] : ['left', 'right']
    return dy >= 0 ? ['bottom', 'top'] : ['top', 'bottom']
  }

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
    edges = app.objects('flows').map((f) => {
      // anchors follow the geometry, so a connection never jumps to a far side of the box
      const [sourceHandle, targetHandle] =
        positions.has(f.source) && positions.has(f.target)
          ? sides(positions.get(f.source)!, positions.get(f.target)!)
          : ['right', 'left']
      const hit = matches(q, f.id, f.title, f.protocol)
      if (q && hit && flowShown(f)) hits.push(f.source, f.target)
      return {
      id: f.id,
      source: f.source,
      target: f.target,
      sourceHandle,
      targetHandle,
      type: 'smoothstep',
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

  async function saveLayout(layout: Record<string, { x: number; y: number }>, notes = currentNotes()) {
    await api('PUT', `/models/${app.modelName}/layout`, { nodes: layout, notes })
    if (app.model) app.model.layout = { nodes: layout, notes }
    await app.refreshProject()
    build()
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
    for (const c of graph.children ?? []) {
      const ox = (c.x ?? 0) + 40
      const oy = (c.y ?? 0) + 40
      if (!c.children?.length) layout[c.id] = { x: Math.round(ox), y: Math.round(oy) }
      for (const g of c.children ?? []) layout[g.id] = { x: Math.round(ox + (g.x ?? 0)), y: Math.round(oy + (g.y ?? 0)) }
    }
    await saveLayout(layout)
    fitView({ maxZoom: 1 })
  }
</script>

<div class="canvas" role="application" bind:this={host} ondragover={(e) => e.preventDefault()} {ondrop}>
  <SvelteFlow
    bind:nodes
    bind:edges
    {nodeTypes}
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
