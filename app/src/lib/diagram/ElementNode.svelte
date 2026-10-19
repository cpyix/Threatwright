<script lang="ts">
  import { Handle, Position, type NodeProps } from '@xyflow/svelte'

  type Data = { id: string; title: string; kind: string; risk: number }
  let { data, selected }: NodeProps & { data: Data } = $props()
</script>

<div class="node kind-{data.kind} risk-{data.risk || 0}" class:selected data-testid="node-{data.id}">
  <span class="id">{data.id}</span>
  <span class="title">{data.title}</span>
  {#each [Position.Top, Position.Right, Position.Bottom, Position.Left] as p}
    <Handle type="source" position={p} id={p} />
  {/each}
</div>

<style>
  .node {
    width: 170px;
    height: 64px;
    display: grid;
    place-content: center;
    text-align: center;
    background: var(--surface);
    border: 1.5px solid var(--text);
    border-radius: 6px;
    color: var(--risk-text, var(--text));
    font-size: 12px;
    padding: 0 8px;
  }
  .risk-0 {
    color: var(--text);
  }
  .risk-1 { background: var(--risk-1); }
  .risk-2 { background: var(--risk-2); }
  .risk-3 { background: var(--risk-3); }
  .risk-4 { background: var(--risk-4); }
  .risk-5 { background: var(--risk-5); }
  .kind-process {
    border-radius: 32px;
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
  .id {
    font-weight: 700;
  }
  .title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 150px;
  }
</style>
