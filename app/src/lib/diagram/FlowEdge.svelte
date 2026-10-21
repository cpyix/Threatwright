<script lang="ts">
  // A data flow: right-angled route through stored bend points, or an automatic smooth step.
  // Selected: drag the bend points, "+" adds one, double-click removes one; the round
  // anchors at both ends move the connection to another side or element.
  import { BaseEdge, EdgeLabel, EdgeReconnectAnchor, getSmoothStepPath, useSvelteFlow, type EdgeProps } from '@xyflow/svelte'
  import { tr } from '../../i18n'
  import { app } from '../../state.svelte'
  import { along, middle, orthogonal, pathOf, snap, stub, type Pt, type Side } from './route'

  type Data = {
    points: Pt[]
    shift: number // offset of parallel connections without own route
    onpoints: (id: string, points: Pt[]) => void
  }
  let {
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    label,
    selected,
    markerStart,
    markerEnd,
    data = { points: [], shift: 0, onpoints: () => {} },
  }: EdgeProps & { data?: Data } = $props()

  const { screenToFlowPosition } = useSvelteFlow()
  let draft = $state<Pt[] | null>(null) // while dragging a bend point
  const points = $derived(draft ?? data.points)
  const a = $derived({ x: sourceX, y: sourceY })
  const b = $derived({ x: targetX, y: targetY })

  const route = $derived.by(() => {
    if (points.length) {
      const line = orthogonal(a, sourcePosition as Side, points, b, targetPosition as Side)
      const m = middle(line)
      return { path: pathOf(line), x: m.x, y: m.y }
    }
    const [path, x, y] = getSmoothStepPath({
      sourceX,
      sourceY,
      targetX,
      targetY,
      sourcePosition,
      targetPosition,
      borderRadius: 6,
      centerX: (sourceX + targetX) / 2 + data.shift,
      centerY: (sourceY + targetY) / 2 + data.shift,
    })
    return { path, x: x + data.shift, y: y + data.shift }
  })

  // "+" on the line between consecutive stops: source, bend points, target
  const inserts = $derived.by(() => {
    const stops = [stub(a, sourcePosition as Side), ...points, stub(b, targetPosition as Side)]
    return stops.slice(1).map((p, i) => {
      const c = stops[i]
      const piece = c.x !== p.x && c.y !== p.y ? [c, { x: p.x, y: c.y }, p] : [c, p] // same elbow as the line
      return { index: i, ...along(piece, 0.25) } // off the middle, where the label sits
    })
  })

  function drag(index: number, event: PointerEvent) {
    event.stopPropagation()
    event.preventDefault()
    const target = event.currentTarget as HTMLElement
    target.setPointerCapture(event.pointerId)
    draft = data.points.map((p) => ({ ...p }))
    const move = (e: PointerEvent) => {
      const p = snap(screenToFlowPosition({ x: e.clientX, y: e.clientY }))
      draft = draft!.map((q, i) => (i === index ? p : q))
    }
    const up = () => {
      target.removeEventListener('pointermove', move)
      target.removeEventListener('pointerup', up)
      const result = draft!
      draft = null
      data.onpoints(id, result)
    }
    target.addEventListener('pointermove', move)
    target.addEventListener('pointerup', up)
  }

  const insert = (index: number, at: Pt) =>
    data.onpoints(id, [...data.points.slice(0, index), snap(at), ...data.points.slice(index)])
  const remove = (index: number) => data.onpoints(id, data.points.filter((_, i) => i !== index))
</script>

<BaseEdge {id} path={route.path} labelX={route.x} labelY={route.y} {label} {markerStart} {markerEnd} interactionWidth={14} />

{#if selected}
  <EdgeReconnectAnchor type="source" position={a} size={14} class="end-anchor" />
  <EdgeReconnectAnchor type="target" position={b} size={14} class="end-anchor" />
  {#each points as p, i (i)}
    <EdgeLabel x={p.x} y={p.y} transparent class="nodrag nopan bend-label">
      <button
        type="button"
        class="bend"
        title={tr(app.lang, 'bend_point_help')}
        aria-label={tr(app.lang, 'bend_point_help')}
        onpointerdown={(e) => drag(i, e)}
        ondblclick={() => remove(i)}
        data-testid="bend-{id}-{i}"
      ></button>
    </EdgeLabel>
  {/each}
  {#each inserts as s (s.index)}
    <EdgeLabel x={s.x} y={s.y} transparent class="nodrag nopan bend-label">
      <button
        type="button"
        class="add"
        title={tr(app.lang, 'bend_point_add')}
        aria-label={tr(app.lang, 'bend_point_add')}
        onclick={() => insert(s.index, s)}
        data-testid="bend-add-{id}-{s.index}">+</button
      >
    </EdgeLabel>
  {/each}
{/if}

<style>
  :global(.bend-label) {
    padding: 0 !important;
    background: none !important;
  }
  .bend,
  .add {
    display: grid;
    place-items: center;
    padding: 0;
    border: 1.5px solid var(--accent);
    background: var(--surface);
    color: var(--accent);
    line-height: 1;
  }
  .bend {
    width: 14px;
    height: 14px;
    border-radius: 2px;
    cursor: move;
  }
  .add {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    font-size: 13px;
    font-weight: 700;
    opacity: 0.75;
    cursor: copy;
  }
  .add:hover {
    opacity: 1;
  }
  :global(.end-anchor) {
    border: 2px solid var(--accent);
    border-radius: 50%;
    background: var(--surface);
    cursor: grab;
  }
</style>
