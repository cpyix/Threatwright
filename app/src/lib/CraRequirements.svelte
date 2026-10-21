<script lang="ts">
  // CRA Annex I: which essential requirement is addressed by which threats and measures.
  import { api, ApiError } from '../api'
  import { tr, type Key } from '../i18n'
  import { app } from '../state.svelte'
  import type { Collection, I18n, ModelPayload } from '../types'

  type Status = 'not_applicable' | 'implemented' | 'planned' | 'threats_only' | 'open'
  type Requirement = {
    id: string
    tr_id: string | null
    title: I18n
    status: Status
    threats: string[]
    measures: string[]
    rationale: string | null
  }

  let rows = $state<Requirement[]>([])
  let editing = $state<string | null>(null)
  let why = $state('')
  let error = $state('')
  const lang = $derived(app.lang)
  const counts = $derived(
    (['open', 'threats_only', 'planned', 'implemented', 'not_applicable'] as Status[]).map(
      (s) => [s, rows.filter((r) => r.status === s).length] as const,
    ),
  )

  $effect(() => {
    void app.model // reload after every change of the model
    api<Requirement[]>('GET', `/models/${app.modelName}/cra`)
      .then((r) => (rows = r))
      .catch((e) => (error = e instanceof ApiError ? e.message : String(e)))
  })

  async function setNotApplicable(id: string, rationale: string | null) {
    error = ''
    const meta = $state.snapshot(app.model!.meta) as ModelPayload['meta']
    const na = { ...(meta.cra_not_applicable ?? {}) }
    if (rationale === null) delete na[id]
    else na[id] = rationale
    try {
      const model = await api<ModelPayload>('PUT', `/models/${app.modelName}/meta`, { ...meta, cra_not_applicable: na })
      editing = null
      why = ''
      await app.afterChange(model)
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e)
    }
  }

  const open = (collection: Collection, id: string) => (app.view = { kind: 'objects', collection, selected: id })
</script>

<section>
  <h1>{tr(lang, 'cra')}</h1>
  <p class="muted help">{tr(lang, 'cra_help')}</p>
  <p class="counts" data-testid="cra-counts">
    {#each counts as [s, n]}<span class="badge st-{s}">{tr(lang, `cra_${s}` as Key)}: {n}</span>{/each}
  </p>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
  <table data-testid="cra-table">
    <thead>
      <tr>
        <th>ID</th><th>{tr(lang, 'title')}</th><th>{tr(lang, 'status')}</th>
        <th>{tr(lang, 'threats')}</th><th>{tr(lang, 'measures')}</th><th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as r (r.id)}
        <tr data-testid="cra-{r.id}">
          <td><strong>{r.id}</strong>{#if r.tr_id}<br /><span class="muted small">{r.tr_id}</span>{/if}</td>
          <td>
            {r.title[lang]}
            {#if r.rationale}<br /><span class="muted small">{tr(lang, 'rationale')}: {r.rationale}</span>{/if}
          </td>
          <td><span class="badge st-{r.status}">{tr(lang, `cra_${r.status}` as Key)}</span></td>
          <td>{#each r.threats as id}<button class="link" onclick={() => open('threats', id)}>{id}</button> {/each}</td>
          <td>{#each r.measures as id}<button class="link" onclick={() => open('measures', id)}>{id}</button> {/each}</td>
          <td class="actions">
            {#if editing === r.id}
              <form onsubmit={(e) => { e.preventDefault(); setNotApplicable(r.id, why) }}>
                <input bind:value={why} required placeholder={tr(lang, 'rationale')} aria-label={tr(lang, 'rationale')} data-testid="cra-why" />
                <button type="submit">{tr(lang, 'apply')}</button>
                <button type="button" onclick={() => (editing = null)}>{tr(lang, 'cancel')}</button>
              </form>
            {:else if r.status === 'not_applicable'}
              <button onclick={() => setNotApplicable(r.id, null)}>{tr(lang, 'reset')}</button>
            {:else if r.status === 'open'}
              <button onclick={() => (editing = r.id)} data-testid="cra-na-{r.id}">{tr(lang, 'set_not_applicable')}</button>
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</section>

<style>
  h1 {
    font-size: 1.3rem;
    margin-top: 0;
  }
  .help {
    max-width: 75ch;
  }
  .counts {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .badge {
    display: inline-block;
    padding: 0.05rem 0.45rem;
    border-radius: var(--radius);
    background: var(--surface-2);
    white-space: nowrap;
  }
  .st-implemented {
    background: var(--risk-1);
    color: var(--risk-text);
  }
  .st-planned {
    background: var(--risk-2);
    color: var(--risk-text);
  }
  .st-threats_only {
    background: var(--risk-3);
    color: var(--risk-text);
  }
  .st-open {
    background: var(--risk-5);
    color: var(--risk-text);
  }
  .small {
    font-size: 0.85em;
  }
  .link {
    border: none;
    background: none;
    color: var(--accent);
    padding: 0;
  }
  .actions form {
    display: flex;
    gap: 0.3rem;
  }
  .actions button {
    white-space: nowrap;
  }
</style>
