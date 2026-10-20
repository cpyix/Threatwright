<script lang="ts">
  import { Handle, Position, type NodeProps } from '@xyflow/svelte'
  import { tr } from '../../i18n'
  import { app } from '../../state.svelte'
  import { iconFor } from '../icons'

  type Data = { id: string; title: string; kind: string; risk: number; icon: string | null; threats: number }
  let { data, selected }: NodeProps & { data: Data } = $props()
  const Icon = $derived(iconFor(data.icon, data.kind))
  const riskText = $derived(
    data.risk ? (app.method?.risk_levels.levels[String(data.risk)]?.[app.lang] ?? String(data.risk)) : '',
  )
  const label = $derived(
    [data.title, data.id, `${data.threats} ${tr(app.lang, 'threats')}`, riskText && `${tr(app.lang, 'risk')} ${data.risk} ${riskText}`]
      .filter(Boolean)
      .join(', '),
  )
</script>

<div
  class="node kind-{data.kind} risk-{data.risk || 0}"
  class:selected
  data-testid="node-{data.id}"
  aria-label={label}
  title={label}
>
  <span class="icon" aria-hidden="true"><Icon size={22} strokeWidth={1.75} /></span>
  <span class="text">
    <span class="title">{data.title}</span>
    <span class="meta">
      {data.id}{#if data.threats}<span class="count">· {data.threats} {tr(app.lang, 'threats_short')}</span>{/if}
    </span>
  </span>
  {#each [Position.Top, Position.Right, Position.Bottom, Position.Left] as p}
    <Handle type="source" position={p} id={p} />
  {/each}
</div>

<style>
  .node {
    width: 170px;
    height: 64px;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    gap: 8px;
    background: var(--surface);
    border: 1.5px solid var(--text);
    border-radius: 6px;
    color: var(--text);
    padding: 0 10px;
    box-shadow: 0 1px 2px rgb(0 0 0 / 0.12);
  }
  .risk-1, .risk-2, .risk-3, .risk-4, .risk-5 {
    color: var(--risk-text);
  }
  .risk-1 { background: var(--risk-1); }
  .risk-2 { background: var(--risk-2); }
  .risk-3 { background: var(--risk-3); }
  .risk-4 { background: var(--risk-4); }
  .risk-5 { background: var(--risk-5); }
  .kind-process {
    border-radius: 32px;
    padding: 0 16px;
  }
  .kind-external {
    border-width: 3px;
    border-radius: 0;
  }
  .kind-datastore {
    border-left: none;
    border-right: none;
    border-radius: 0;
  }
  .selected {
    outline: 2px solid var(--focus);
    outline-offset: 2px;
  }
  .icon {
    display: grid;
    place-items: center;
  }
  .text {
    display: grid;
    min-width: 0;
    line-height: 1.2;
  }
  .title {
    font-size: 13px;
    font-weight: 650;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .meta {
    font-size: 11px;
    opacity: 0.8;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .count {
    margin-left: 0.25em;
  }
</style>
