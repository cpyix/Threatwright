<script lang="ts">
  import type { NodeProps } from '@xyflow/svelte'

  let { data }: NodeProps & { data: { id: string; title: string; width: number; height: number; variant?: 'zone' | 'host' | 'context' } } = $props()
</script>

<div class="zone {data.variant ?? 'zone'}" style:width="{data.width}px" style:height="{data.height}px" data-testid="{data.variant ?? 'zone'}-{data.id}">
  <span>{data.title}</span>
</div>

<style>
  .zone {
    border: 1.5px dashed var(--muted);
    border-radius: 8px;
    pointer-events: none;
  }
  /* a device and what runs on it (runs_on) */
  .host {
    border: 1.5px solid var(--accent, #2f5f8a);
  }
  /* processes with the same rights on that host */
  .context {
    border: 1.5px dotted var(--accent, #2f5f8a);
    border-radius: 6px;
  }
  .host span,
  .context span {
    color: var(--accent, #2f5f8a);
    font-size: 11px;
  }
  span {
    position: absolute;
    top: 4px;
    left: 8px;
    color: var(--muted);
    font-size: 12px;
  }
</style>
