<script lang="ts">
  // Zones (with default environment), configurations and changelog of a model.
  import { api, ApiError } from '../api'
  import { tr } from '../i18n'
  import { app } from '../state.svelte'
  import type { ModelPayload } from '../types'

  type Meta = Record<string, any>
  let draft = $state<Meta>({})
  let error = $state('')
  let version = $state('')
  let summary = $state('')
  const lang = $derived(app.lang)
  const indicators = ['interface', 'access', 'user'] as const

  $effect(() => {
    draft = structuredClone($state.snapshot(app.model?.meta ?? {})) as Meta
  })

  async function save(meta: Meta = draft) {
    error = ''
    try {
      const model = await api<ModelPayload>('PUT', `/models/${app.modelName}/meta`, meta)
      await app.afterChange(model)
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e)
    }
  }

  function nextId(prefix: string, items: { id: string }[]) {
    let n = items.length + 1
    while (items.some((i) => i.id === `${prefix}-${n}`)) n++
    return `${prefix}-${n}`
  }

  function addVersion() {
    const today = new Date().toISOString().slice(0, 10)
    const meta = $state.snapshot(draft) as Meta
    meta.changelog = [...(meta.changelog ?? []), { version, date: today, summary }]
    version = ''
    summary = ''
    save(meta)
  }
</script>

<h2>{tr(lang, 'zones')}</h2>
<table>
  <thead>
    <tr><th>ID</th><th>{tr(lang, 'title')}</th>{#each indicators as i}<th>{tr(lang, i)}</th>{/each}<th></th></tr>
  </thead>
  <tbody>
    {#each draft.zones ?? [] as zone, n}
      <tr>
        <td><input bind:value={zone.id} aria-label="ID" /></td>
        <td><input bind:value={zone.title} aria-label={tr(lang, 'title')} /></td>
        {#each indicators as i}
          <td>
            <select
              value={zone.environment?.[i] ?? ''}
              onchange={(e) => {
                zone.environment = { ...(zone.environment ?? {}), [i]: e.currentTarget.value || null }
              }}
              aria-label={tr(lang, i)}
            >
              <option value="">–</option>
              {#each Object.entries(app.method?.[i].values ?? {}) as [key, v]}<option value={key}>{v[lang]}</option>{/each}
            </select>
          </td>
        {/each}
        <td><button onclick={() => draft.zones.splice(n, 1)} aria-label={tr(lang, 'remove')}>×</button></td>
      </tr>
    {/each}
  </tbody>
</table>
<button onclick={() => (draft.zones = [...(draft.zones ?? []), { id: nextId('Z', draft.zones ?? []), title: '', environment: {} }])}>+ {tr(lang, 'zone')}</button>

<h2>{tr(lang, 'configurations')}</h2>
<table>
  <tbody>
    {#each draft.configurations ?? [] as c, n}
      <tr>
        <td><input bind:value={c.id} aria-label="ID" /></td>
        <td><input bind:value={c.title} aria-label={tr(lang, 'title')} /></td>
        <td><button onclick={() => draft.configurations.splice(n, 1)} aria-label={tr(lang, 'remove')}>×</button></td>
      </tr>
    {/each}
  </tbody>
</table>
<button onclick={() => (draft.configurations = [...(draft.configurations ?? []), { id: nextId('K', draft.configurations ?? []), title: '' }])}>+ {tr(lang, 'configurations')}</button>
<p><button class="primary" onclick={() => save()} data-testid="save-meta">{tr(lang, 'apply')}</button></p>
{#if error}<pre class="error" role="alert">{error}</pre>{/if}

<h2>{tr(lang, 'changelog')}</h2>
<ul>
  {#each [...(draft.changelog ?? [])].reverse() as entry}
    <li><strong>{entry.version}</strong> ({entry.date}) {entry.summary}</li>
  {/each}
</ul>
<form class="row" onsubmit={(e) => { e.preventDefault(); addVersion() }}>
  <input bind:value={version} required placeholder={tr(lang, 'version')} aria-label={tr(lang, 'version')} />
  <input bind:value={summary} required placeholder={tr(lang, 'summary')} aria-label={tr(lang, 'summary')} />
  <button type="submit">{tr(lang, 'new_version')}</button>
</form>

<style>
  h2 {
    font-size: 1.05rem;
    margin-top: 1.5rem;
  }
  td input,
  td select {
    min-width: 6rem;
  }
  .row {
    display: flex;
    gap: 0.5rem;
  }
  .row input:first-child {
    max-width: 8rem;
  }
  .row button {
    white-space: nowrap;
  }
</style>
