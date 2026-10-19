<script lang="ts">
  import type { Option } from '../fields'

  let {
    id,
    options,
    value = [],
    onchange,
  }: { id: string; options: Option[]; value: string[]; onchange: (v: string[]) => void } = $props()

  let filter = $state('')
  const shown = $derived(
    options.filter(
      (o) => value.includes(o.value) || o.label.toLowerCase().includes(filter.toLowerCase()),
    ),
  )

  function toggle(v: string, on: boolean) {
    onchange(on ? [...value, v] : value.filter((x) => x !== v))
  }
</script>

<div class="multi" role="group" aria-labelledby="{id}-label">
  {#if options.length > 8}
    <input class="filter" type="search" placeholder="…" bind:value={filter} aria-label="filter" />
  {/if}
  <div class="items">
    {#each shown as o (o.value)}
      <label>
        <input
          type="checkbox"
          checked={value.includes(o.value)}
          onchange={(e) => toggle(o.value, e.currentTarget.checked)}
        />
        {o.label}
      </label>
    {:else}
      <span class="muted">–</span>
    {/each}
  </div>
</div>

<style>
  .multi {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    padding: 0.25rem 0.5rem;
  }
  .items {
    max-height: 9rem;
    overflow: auto;
    display: flex;
    flex-wrap: wrap;
    gap: 0.1rem 0.9rem;
  }
  label {
    display: flex;
    gap: 0.35rem;
    align-items: baseline;
    min-width: 0;
  }
  label input {
    width: auto;
  }
  .filter {
    margin-bottom: 0.25rem;
  }
</style>
