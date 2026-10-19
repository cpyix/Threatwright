<script lang="ts">
  // Status board for measures: proposed -> decided -> in progress -> implemented.
  import { api } from '../api'
  import { label, tr } from '../i18n'
  import { app } from '../state.svelte'
  import type { ModelPayload, Obj } from '../types'

  let { onselect }: { onselect: (id: string) => void } = $props()

  const STATES = ['proposed', 'decided', 'in_progress', 'implemented']
  const lang = $derived(app.lang)
  const threatsOf = (id: string) => app.objects('threats').filter((t) => t.measures?.includes(id)).length

  async function move(m: Obj, step: number) {
    const status = STATES[STATES.indexOf(m.status ?? 'proposed') + step]
    const r = await api<{ model: ModelPayload }>('PUT', `/models/${app.modelName}/measures/${m.id}`, {
      ...$state.snapshot(m),
      status,
    })
    await app.afterChange(r.model)
  }
</script>

<div class="board" data-testid="measure-board">
  {#each STATES as state, i}
    <section aria-label={label(lang, state)}>
      <h2>{label(lang, state)} <span class="muted">{app.objects('measures').filter((m) => (m.status ?? 'proposed') === state).length}</span></h2>
      {#each app.objects('measures').filter((m) => (m.status ?? 'proposed') === state) as m (m.id)}
        <article>
          <button class="rowlink" onclick={() => onselect(m.id)}>{m.id}</button>
          <p>{m.title}</p>
          <p class="muted">{m.owner ?? ''} {m.due ? `· ${m.due}` : ''} · {threatsOf(m.id)} {tr(lang, 'threats')}</p>
          <div class="moves">
            <button disabled={i === 0} onclick={() => move(m, -1)} aria-label="←">←</button>
            <button disabled={i === STATES.length - 1} onclick={() => move(m, 1)} aria-label="→">→</button>
          </div>
        </article>
      {/each}
    </section>
  {/each}
</div>

<style>
  .board {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
    align-items: start;
  }
  h2 {
    font-size: 0.95rem;
    margin: 0 0 0.5rem;
  }
  article {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.5rem;
    margin-bottom: 0.5rem;
  }
  article p {
    margin: 0.2rem 0;
  }
  .moves {
    display: flex;
    gap: 0.3rem;
    justify-content: flex-end;
  }
  .rowlink {
    border: none;
    background: none;
    padding: 0;
    color: var(--accent);
    font-weight: 600;
  }
</style>
