<script lang="ts">
  import {
    Background,
    ConnectionMode,
    Controls,
    MarkerType,
    SvelteFlow,
    useSvelteFlow,
    type Edge,
    type Node,
  } from '@xyflow/svelte'
  import { api } from '../../api'
  import { app } from '../../state.svelte'
  import type { ElementType, ModelPayload } from '../../types'
  import Legend from './Legend.svelte'
  import ElementNode from './ElementNode.svelte'
  import ZoneNode from './ZoneNode.svelte'

  let {
    flowType,
    configuration,
    types,
    onselect,
  }: {
    flowType: string
    configuration: string[] // selected variants; empty = all
    types: ElementType[]
    onselect: (collection: 'elements' | 'flows', id: string | null) => void
  } = $props()

  const W = 170
  const H = 64
  const PAD = 24
  const nodeTypes = { element: ElementNode, zone: ZoneNode }
  const { screenToFlowPosition, fitView } = useSvelteFlow()

  let nodes = $state.raw<Node[]>([])
  let edges = $state.raw<Edge[]>([])

  // objects without variants belong to every variant
  const visible = (configs: string[] | undefined) =>
    !configuration.length || !configs?.length || configs.some((c) => configuration.includes(c))

  /** Handles facing each other: side by side -> right/left, above each other -> bottom/top. */
  function sides(a: { x: number; y: number }, b: { x: number; y: number }): [string, string] {
    const dx = b.x - a.x
    const dy = b.y - a.y
    if (Math.abs(dx) * H >= Math.abs(dy) * W) return dx >= 0 ? ['right', 'left'] : ['left', 'right']
    return dy >= 0 ? ['bottom', 'top'] : ['top', 'bottom']
  }

  function zoneNodes(positions: Map<string, { x: number; y: number }>): Node[] {
    const out: Node[] = []
    for (const zone of app.model?.meta.zones ?? []) {
      const members = app
        .objects('elements')
        .filter((e) => e.zone === zone.id && positions.has(e.id) && visible(e.configurations))
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
    const icons = new Map(types.map((t) => [t.id, t.icon]))
    const threats = new Map<string, number>()
    for (const t of app.objects('threats')) for (const id of t.targets ?? []) threats.set(id, (threats.get(id) ?? 0) + 1)
    const elementNodes: Node[] = app.objects('elements').map((e) => ({
      id: e.id,
      type: 'element',
      position: positions.get(e.id)!,
      data: {
        id: e.id,
        title: e.title,
        kind: e.kind,
        risk: model.max_risks[e.id] ?? 0,
        icon: icons.get(/element\/([^@]+)@/.exec(e.library_ref ?? '')?.[1] ?? '') ?? null,
        threats: threats.get(e.id) ?? 0,
      },
      hidden: !visible(e.configurations),
    }))
    nodes = [...zoneNodes(positions), ...elementNodes]
    const zoneOf = new Map(app.objects('elements').map((e) => [e.id, e.zone]))
    edges = app.objects('flows').map((f) => {
      // anchors follow the geometry, so a connection never jumps to a far side of the box
      const [sourceHandle, targetHandle] =
        positions.has(f.source) && positions.has(f.target)
          ? sides(positions.get(f.source)!, positions.get(f.target)!)
          : ['right', 'left']
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
      hidden: !visible(f.configurations),
      class: [
        (model.max_risks[f.id] ?? 0) >= 4 ? 'high-risk' : '',
        zoneOf.get(f.source) !== zoneOf.get(f.target) ? 'cross-zone' : '',
      ].join(' '),
      }
    })
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

  async function ondragstop({ targetNode }: { targetNode: Node | null }) {
    // hit-test against the boxes as drawn before the drag; saving the layout redraws them
    const zone = targetNode?.type === 'element' ? zoneAt(targetNode.position.x + W / 2, targetNode.position.y + H / 2) : null
    await saveLayout(currentLayout())
    const element = app.objects('elements').find((e) => e.id === targetNode?.id)
    if (!element || !zone || zone === element.zone) return
    // ponytail: leaving a zone into empty space keeps the zone (its box grows); reassigning needs a target zone
    const r = await api<{ model: ModelPayload }>('PUT', `/models/${app.modelName}/elements/${element.id}`, {
      ...$state.snapshot(element),
      zone,
    })
    await app.afterChange(r.model)
  }

  $effect(() => {
    void app.model
    void configuration
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

  async function saveLayout(layout: Record<string, { x: number; y: number }>) {
    await api('PUT', `/models/${app.modelName}/layout`, { nodes: layout })
    if (app.model) app.model.layout = { nodes: layout }
    await app.refreshProject()
    build()
  }

  async function onconnect(c: { source: string; target: string }) {
    if (c.source === c.target) return
    const r = await api<{ id: string; model: ModelPayload }>('POST', `/models/${app.modelName}/add/flow`, {
      source: c.source,
      target: c.target,
      type: flowType || null,
    })
    await app.afterChange(r.model)
    onselect('flows', r.id)
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
    await app.afterChange(r.model)
    onselect('elements', r.id)
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
    onnodedragstop={ondragstop}
    onnodeclick={({ node }) => node.type === 'element' && onselect('elements', node.id)}
    onedgeclick={({ edge }) => onselect('flows', edge.id)}
    onpaneclick={() => onselect('elements', null)}
    {onconnect}
  >
    <Background />
    <Controls />
    <Legend />
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
