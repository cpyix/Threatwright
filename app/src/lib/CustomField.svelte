<script lang="ts">
  // One field from custom-fields.yaml, rendered by its type.
  import { app } from '../state.svelte'
  import type { CustomField } from '../types'
  import MultiSelect from './MultiSelect.svelte'

  let { field, value, set }: { field: CustomField; value: any; set: (v: any) => void } = $props()

  const id = $derived(`custom-${field.name}`)
  const refs = $derived(
    [...app.objects('elements'), ...app.objects('flows'), ...app.objects('assets'), ...app.objects('threats'),
     ...app.objects('measures'), ...app.objects('questions')].map((o) => ({ value: o.id, label: `${o.id} ${o.title}` })),
  )
  const options = $derived(field.options.map((o) => ({ value: o, label: o })))
</script>

{#if field.type === 'bool'}
  <input {id} type="checkbox" checked={!!value} onchange={(e) => set(e.currentTarget.checked)} />
{:else if field.type === 'longtext'}
  <textarea {id} value={value ?? ''} oninput={(e) => set(e.currentTarget.value)}></textarea>
{:else if field.type === 'number'}
  <input {id} type="number" value={value ?? ''} oninput={(e) => set(e.currentTarget.value === '' ? '' : Number(e.currentTarget.value))} />
{:else if field.type === 'date'}
  <input {id} type="date" value={value ?? ''} oninput={(e) => set(e.currentTarget.value)} />
{:else if field.type === 'choice'}
  <select {id} value={value ?? ''} onchange={(e) => set(e.currentTarget.value)}>
    <option value="">–</option>
    {#each field.options as o}<option value={o}>{o}</option>{/each}
  </select>
{:else if field.type === 'multichoice'}
  <MultiSelect {id} {options} value={value ?? []} onchange={set} />
{:else if field.type === 'reference'}
  <MultiSelect {id} options={refs} value={Array.isArray(value) ? value : value ? [value] : []} onchange={set} />
{:else}
  <input {id} value={value ?? ''} oninput={(e) => set(e.currentTarget.value)} />
{/if}
