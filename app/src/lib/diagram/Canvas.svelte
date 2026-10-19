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
  import type { ModelPayload } from '../../types'
  import ElementNode from './ElementNode.svelte'
  import ZoneNode from './ZoneNode.svelte'

  let {
    flowType,
    configuration,
    onselect,
  }: {
    flowType: string
    configuration: string
    onselect: (collection: 'elements' | 'flows', id: string | null) => void
  } = $props()

  const W = 170
  const H = 64
  const PAD = 24
  const nodeTypes = { element: ElementNode, zone: ZoneNode }
  const { screenToFlowPosition, fitView } = useSvelteFlow()

  let nodes = $state.raw<Node[]>([])
  let edges = $state.raw<Edge[]>([])

  const visible = (configs: string[] | undefined) =>
    !configuration || !configs?.length || configs.includes(configuration)

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
        data: { title: zone.title, width: x1 - x0, height: y1 - y0 },
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
    const elementNodes: Node[] = app.objects('elements').map((e) => ({
      id: e.id,
      type: 'element',
      position: positions.get(e.id)!,
      data: { id: e.id, title: e.title, kind: e.kind, risk: model.max_risks[e.id] ?? 0 },
      hidden: !visible(e.configurations),
    }))
    nodes = [...zoneNodes(positions), ...elementNodes]
    edges = app.objects('flows').map((f) => ({
      id: f.id,
      source: f.source,
      target: f.target,
      label: `${f.id} ${f.title}`,
      markerEnd: { type: MarkerType.ArrowClosed },
      markerStart: f.bidirectional ? { type: MarkerType.ArrowClosed } : undefined,
      hidden: !visible(f.configurations),
      class: (model.max_risks[f.id] ?? 0) >= 4 ? 'high-risk' : '',
    }))
  }

  $effect(() => {
    void app.model
    void configuration
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

  async function ondrop(event: DragEvent) {
    event.preventDefault()
    const type = event.dataTransfer?.getData('application/x-threatwright-type')
    if (!type) return
    const p = screenToFlowPosition({ x: event.clientX, y: event.clientY })
    const r = await api<{ id: string; model: ModelPayload }>('POST', `/models/${app.modelName}/add/element`, {
      type,
      x: Math.round(p.x - W / 2),
      y: Math.round(p.y - H / 2),
    })
    await app.afterChange(r.model)
    onselect('elements', r.id)
  }

  export async function autoLayout() {
    const { default: ELK } = await import('elkjs/lib/elk.bundled.js') // loaded on demand
    const elk = new ELK()
    const graph = await elk.layout({
      id: 'root',
      layoutOptions: {
        'elk.algorithm': 'layered',
        'elk.direction': 'RIGHT',
        'elk.spacing.nodeNode': '60',
        'elk.layered.spacing.nodeNodeBetweenLayers': '100',
      },
      children: app.objects('elements').map((e) => ({ id: e.id, width: W, height: H })),
      edges: app.objects('flows').map((f) => ({ id: f.id, sources: [f.source], targets: [f.target] })),
    })
    const layout: Record<string, { x: number; y: number }> = {}
    for (const c of graph.children ?? []) layout[c.id] = { x: Math.round(c.x ?? 0) + 40, y: Math.round(c.y ?? 0) + 40 }
    await saveLayout(layout)
    fitView()
  }
</script>

<div class="canvas" role="application" ondragover={(e) => e.preventDefault()} {ondrop}>
  <SvelteFlow
    bind:nodes
    bind:edges
    {nodeTypes}
    connectionMode={ConnectionMode.Loose}
    deleteKey={null}
    fitView
    onnodedragstop={() => saveLayout(currentLayout())}
    onnodeclick={({ node }) => node.type === 'element' && onselect('elements', node.id)}
    onedgeclick={({ edge }) => onselect('flows', edge.id)}
    onpaneclick={() => onselect('elements', null)}
    {onconnect}
  >
    <Background />
    <Controls />
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
  .canvas :global(.svelte-flow__edge-label) {
    background: var(--surface);
    color: var(--text);
    font-size: 11px;
  }
  .canvas :global(.svelte-flow) {
    --xy-background-color: var(--surface);
  }
</style>
