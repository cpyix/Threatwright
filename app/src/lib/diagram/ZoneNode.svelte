<script lang="ts">
  import type { NodeProps } from '@xyflow/svelte'

  let { data }: NodeProps & { data: { id: string; title: string; width: number; height: number } } = $props()
</script>

<div class="zone" style:width="{data.width}px" style:height="{data.height}px" data-testid="zone-{data.id}">
  <span>{data.title}</span>
</div>

<style>
  .zone {
    border: 1.5px dashed var(--muted);
    border-radius: 8px;
    pointer-events: none;
  }
  span {
    position: absolute;
    top: 4px;
    left: 8px;
    color: var(--muted);
    font-size: 12px;
  }
</style>
