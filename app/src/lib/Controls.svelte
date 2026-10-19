<script lang="ts">
  // ARC applicability (TR-03183-1 section 6.2) of imported controls, with manual override.
  import { api, ApiError } from '../api'
  import { tr } from '../i18n'
  import { app } from '../state.svelte'
  import type { I18n } from '../types'

  type Control = {
    measure_id: string
    control_id: string | null
    applies: boolean
    rationale: I18n
    overridden: boolean
  }

  let rows = $state<Control[]>([])
  let editing = $state<string | null>(null)
  let why = $state('')
  let error = $state('')
  const lang = $derived(app.lang)

  async function load() {
    error = ''
    try {
      rows = await api<Control[]>('GET', `/models/${app.modelName}/controls`)
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e)
    }
  }

  $effect(() => {
    void app.modelName
    load()
  })

  async function override(id: string, applies: boolean | null) {
    const body = applies === null ? null : { applies, rationale: why, by: null }
    rows = await api<Control[]>('PUT', `/arc/${app.modelName}/${id}`, body)
    editing = null
    why = ''
  }
</script>

<section>
  <h1>{tr(lang, 'controls')}</h1>
  <p class="muted">{tr(lang, 'controls_help')}</p>
  {#if error}<p class="error">{error}</p>{/if}
  {#if rows.length === 0}
    <p class="muted">{tr(lang, 'no_controls')}</p>
  {:else}
    <table>
      <thead>
        <tr><th>Control</th><th>{tr(lang, 'applies')}</th><th>{tr(lang, 'rationale')}</th><th></th></tr>
      </thead>
      <tbody>
        {#each rows as c (c.measure_id)}
          <tr>
            <td><strong>{c.control_id ?? c.measure_id}</strong></td>
            <td class={c.applies ? 'ok' : 'muted'}>{c.applies ? '✓' : '–'} {#if c.overridden}<span class="muted">({tr(lang, 'manual')})</span>{/if}</td>
            <td>{c.rationale[lang]}</td>
            <td class="actions">
              {#if editing === c.measure_id}
                <form onsubmit={(e) => { e.preventDefault(); override(c.measure_id, !c.applies) }}>
                  <input bind:value={why} required placeholder={tr(lang, 'rationale')} aria-label={tr(lang, 'rationale')} />
                  <button type="submit">{c.applies ? tr(lang, 'set_not_applicable') : tr(lang, 'set_applicable')}</button>
                </form>
              {:else if c.overridden}
                <button onclick={() => override(c.measure_id, null)}>{tr(lang, 'reset')}</button>
              {:else}
                <button onclick={() => (editing = c.measure_id)}>{tr(lang, 'override')}</button>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</section>

<style>
  h1 {
    font-size: 1.3rem;
    margin-top: 0;
  }
  .actions form {
    display: flex;
    gap: 0.3rem;
  }
  .actions button {
    white-space: nowrap;
  }
</style>
