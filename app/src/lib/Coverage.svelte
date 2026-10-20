<script lang="ts">
  import { api } from '../api'
  import { label, tr } from '../i18n'
  import { app } from '../state.svelte'
  import type { CoverageRow, ModelPayload } from '../types'
  import Info from './Info.svelte'

  let rows = $state<CoverageRow[]>([])
  let marking = $state<{ id: string; s: string } | null>(null)
  let rationale = $state('')
  const lang = $derived(app.lang)

  $effect(() => {
    void app.model
    api<CoverageRow[]>('GET', `/models/${app.modelName}/coverage`).then((r) => (rows = r))
  })

  async function setNotRelevant(row: CoverageRow, s: string, why: string | null) {
    const collection = row.kind === 'flow' ? 'flows' : 'elements'
    const obj = app.objects(collection).find((o) => o.id === row.id)
    if (!obj) return
    const marks = { ...(obj.stride_not_relevant ?? {}) }
    if (why) marks[s] = why
    else delete marks[s]
    const r = await api<{ model: ModelPayload }>('PUT', `/models/${app.modelName}/${collection}/${row.id}`, {
      ...$state.snapshot(obj),
      stride_not_relevant: marks,
    })
    marking = null
    rationale = ''
    await app.afterChange(r.model)
  }
</script>

<section>
  <h1>{tr(lang, 'coverage')} <Info term="coverage" /> <Info term="stride" /></h1>
  <table class="matrix" data-testid="coverage">
    <thead>
      <tr>
        <th>{tr(lang, 'elements')} / {tr(lang, 'flows')}</th>
        {#each 'STRIDE' as s}<th title={label(lang, s)}>{s}</th>{/each}
      </tr>
    </thead>
    <tbody>
      {#each rows as row (row.id)}
        <tr>
          <th scope="row"><span class="muted">{row.id}</span> {row.title}</th>
          {#each 'STRIDE' as s}
            {@const cell = row.cells[s]}
            <td class:gap={cell.relevant && !cell.existing.length && !cell.not_relevant}>
              {#if cell.existing.length}
                <button class="count" onclick={() => (app.view = { kind: 'assistant', target: row.id })}>{cell.existing.length}</button>
              {:else if cell.not_relevant}
                <span title={cell.not_relevant}>{tr(lang, 'not_relevant_short')}</span>
                <button class="mini" aria-label={tr(lang, 'remove')} onclick={() => setNotRelevant(row, s, null)}>×</button>
              {:else if !cell.relevant}
                <span class="muted" title={tr(lang, 'not_applicable')}>·</span>
              {:else if marking?.id === row.id && marking.s === s}
                <form onsubmit={(e) => { e.preventDefault(); setNotRelevant(row, s, rationale) }}>
                  <input bind:value={rationale} placeholder={tr(lang, 'rationale')} required aria-label={tr(lang, 'rationale')} />
                  <button type="submit" class="mini">✓</button>
                </form>
              {:else}
                <button class="mini" onclick={() => (app.view = { kind: 'assistant', target: row.id })} title={tr(lang, 'open_assistant')}>+</button>
                <button class="mini" onclick={() => (marking = { id: row.id, s })} title={tr(lang, 'mark_not_relevant')}>{tr(lang, 'not_relevant_short')}</button>
              {/if}
            </td>
          {/each}
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
  .matrix td,
  .matrix th {
    text-align: center;
  }
  .matrix th[scope='row'] {
    text-align: left;
    font-weight: normal;
    color: var(--text);
  }
  td.gap {
    background: var(--risk-3);
  }
  .count {
    font-weight: 700;
    min-width: 2rem;
  }
  .mini {
    padding: 0 0.35rem;
    font-size: 0.85em;
  }
  form {
    display: flex;
    gap: 0.25rem;
  }
  form input {
    min-width: 8rem;
  }
</style>
