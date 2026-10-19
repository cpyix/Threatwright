<script lang="ts">
  import { COLUMNS, getPath, NEW } from '../fields'
  import { label, tr, type Key } from '../i18n'
  import { app } from '../state.svelte'
  import type { Collection, Obj } from '../types'
  import ObjectForm from './ObjectForm.svelte'
  import RiskBadge from './RiskBadge.svelte'

  let { collection, selected }: { collection: Collection; selected: string | null } = $props()

  let filter = $state('')
  let draft = $state<Partial<Obj> | null>(null)
  const lang = $derived(app.lang)
  const rows = $derived(
    app
      .objects(collection)
      .filter((o) => JSON.stringify(o).toLowerCase().includes(filter.toLowerCase())),
  )
  const current = $derived(
    draft ?? (selected ? app.objects(collection).find((o) => o.id === selected) : null),
  )

  function select(id: string | null) {
    draft = null
    app.view = { kind: 'objects', collection, selected: id }
  }

  // Rule 3.3: ask for new threats unless the form already answered it.
  function afterSave(id: string, created: boolean) {
    select(id)
    const threat = app.objects('threats').find((t) => t.id === id)
    if (created && collection === 'threats' && threat?.cyber_cause == null) app.cyberCheck = id
  }

  function cell(o: Obj, col: string): string {
    const v = getPath(o, col)
    return Array.isArray(v) ? v.join(' ') : v == null ? '' : label(lang, String(v))
  }
</script>

<section class="objects">
  <div class="list">
    <div class="toolbar">
      <h1>{tr(lang, collection)}</h1>
      <button class="primary" onclick={() => (draft = NEW[collection]())} data-testid="new-object">
        + {tr(lang, 'new')}
      </button>
    </div>
    <input type="search" placeholder={tr(lang, 'filter')} bind:value={filter} aria-label={tr(lang, 'filter')} />
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>{tr(lang, 'title')}</th>
          {#each COLUMNS[collection] as c}<th>{tr(lang, c as Key)}</th>{/each}
          {#if collection === 'threats'}<th>{tr(lang, 'risk')}</th>{/if}
        </tr>
      </thead>
      <tbody>
        {#each rows as o (o.id)}
          <tr class:active={o.id === current?.id}>
            <td class="id">
              <button class="rowlink" onclick={() => select(o.id)}>{o.id}</button>
              {#if app.changed.has(o.id)}<span class="changed" title={tr(lang, 'changed')}>●</span>{/if}
            </td>
            <td>{o.title}</td>
            {#each COLUMNS[collection] as c}<td>{cell(o, c)}</td>{/each}
            {#if collection === 'threats'}
              <td><RiskBadge risk={app.model?.evaluations[o.id]?.assessment.risk} /></td>
            {/if}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <div class="detail">
    {#if current}
      {#key `${current.id ?? 'new'}-${collection}`}
        <ObjectForm {collection} source={current} onsaved={(id, created) => afterSave(id, created)} onclose={() => select(null)} />
      {/key}
    {/if}
  </div>
</section>

<style>
  .objects {
    display: grid;
    grid-template-columns: minmax(20rem, 1fr) minmax(24rem, 1.1fr);
    gap: 1rem;
    align-items: start;
  }
  .list,
  .detail {
    min-width: 0;
  }
  td.id {
    white-space: nowrap;
  }
  .changed {
    color: var(--accent);
    font-size: 0.8em;
    margin-left: 0.25rem;
  }
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  h1 {
    font-size: 1.3rem;
    margin: 0 0 0.5rem;
  }
  .list input {
    margin-bottom: 0.5rem;
  }
  .rowlink {
    border: none;
    background: none;
    padding: 0;
    color: var(--accent);
    font-weight: 600;
  }
  tr.active td {
    background: var(--surface-2);
  }
  .detail {
    position: sticky;
    top: 0.5rem;
    max-height: calc(100vh - 5rem);
    overflow: auto;
    padding-right: 0.25rem;
  }
  @media (max-width: 900px) {
    .objects {
      grid-template-columns: 1fr;
    }
  }
</style>
