<script lang="ts">
  import { api, ApiError } from '../api'
  import { tr } from '../i18n'
  import { app } from '../state.svelte'

  type Imported = { library: string; title: string; version: string; source: string; entries: number }

  let items = $state<Imported[]>([])
  let path = $state('')
  let kind = $state<'catalog' | 'profile' | 'component'>('catalog')
  let note = $state('')
  const lang = $derived(app.lang)

  async function load() {
    items = await api<Imported[]>('GET', '/oscal/imported').catch(() => [])
  }

  $effect(() => {
    void app.project
    load()
  })

  async function run() {
    note = ''
    try {
      const r = await api<{ written: string; issues: string[] }>('POST', '/oscal/import', { path, as: kind })
      note = `${tr(lang, 'imported')}: ${r.written}`
      await app.loadProject(await api('POST', '/reload'))
      await load()
    } catch (e) {
      note = e instanceof ApiError ? e.message : String(e)
    }
  }
</script>

<h2>{tr(lang, 'catalogs')}</h2>
<p class="muted">{tr(lang, 'catalogs_help')}</p>
{#if items.length}
  <table>
    <thead><tr><th>{tr(lang, 'name')}</th><th>Version</th><th>{tr(lang, 'source')}</th><th>{tr(lang, 'count')}</th></tr></thead>
    <tbody>
      {#each items as c}
        <tr><td>{c.title} <span class="muted">({c.library})</span></td><td>{c.version}</td><td>{c.source}</td><td>{c.entries}</td></tr>
      {/each}
    </tbody>
  </table>
{/if}
<form class="row" onsubmit={(e) => { e.preventDefault(); run() }}>
  <input placeholder={tr(lang, 'catalog_path')} bind:value={path} required aria-label={tr(lang, 'catalog_path')} />
  <select bind:value={kind} aria-label={tr(lang, 'import_as')}>
    <option value="catalog">Catalog</option>
    <option value="profile">Profile</option>
    <option value="component">Component Definition</option>
  </select>
  <button type="submit">{tr(lang, 'import')}</button>
</form>
{#if note}<pre class="note" role="status">{note}</pre>{/if}

<style>
  h2 {
    font-size: 1.05rem;
    margin-top: 1.5rem;
  }
  .row {
    display: flex;
    gap: 0.5rem;
    margin: 0.5rem 0;
  }
  .row input {
    flex: 1;
  }
  .row select {
    width: auto;
  }
  .note {
    white-space: pre-wrap;
  }
</style>
