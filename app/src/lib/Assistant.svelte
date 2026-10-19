<script lang="ts">
  import { api } from '../api'
  import { label, tr } from '../i18n'
  import { app } from '../state.svelte'
  import type { Category, ModelPayload } from '../types'

  let { target }: { target: string | null } = $props()

  let categories = $state<Record<string, Category> | null>(null)
  let busy = $state(false)
  const lang = $derived(app.lang)
  const targets = $derived([...app.objects('elements'), ...app.objects('flows')])
  const threatTitle = (id: string) => app.objects('threats').find((t) => t.id === id)?.title ?? ''

  async function load() {
    categories = target
      ? (await api<{ categories: Record<string, Category> }>('GET', `/models/${app.modelName}/assistant/${target}`)).categories
      : null
  }

  $effect(() => {
    void target
    void app.model
    load()
  })

  async function adopt(template: string) {
    busy = true
    try {
      const r = await api<{ id: string; model: ModelPayload }>(
        'POST',
        `/models/${app.modelName}/assistant/${target}`,
        { template },
      )
      await app.afterChange(r.model)
      app.cyberCheck = r.id
    } finally {
      busy = false
    }
  }
</script>

<section>
  <h1>{tr(lang, 'assistant')}</h1>
  <label for="assistant-target">{tr(lang, 'select_target')}</label>
  <select
    id="assistant-target"
    value={target ?? ''}
    onchange={(e) => (app.view = { kind: 'assistant', target: e.currentTarget.value || null })}
    data-testid="assistant-target"
  >
    <option value="">–</option>
    {#each targets as o}<option value={o.id}>{o.id} {o.title}</option>{/each}
  </select>

  {#if categories}
    {#each Object.entries(categories) as [s, cat] (s)}
      {#if cat.relevant || cat.existing.length}
        <details open={cat.relevant && cat.existing.length === 0} class:done={cat.existing.length > 0 || !!cat.not_relevant}>
          <summary>
            <strong>{s}</strong> {label(lang, s)}
            <span class="muted">· {cat.existing.length} · {cat.suggestions.length}</span>
            {#if cat.not_relevant}<span class="muted">· {tr(lang, 'not_relevant')}</span>{/if}
          </summary>
          {#if cat.existing.length}
            <h3>{tr(lang, 'existing')}</h3>
            <ul>
              {#each cat.existing as id}
                <li>
                  <button class="rowlink" onclick={() => (app.view = { kind: 'objects', collection: 'threats', selected: id })}>{id}</button>
                  {threatTitle(id)}
                </li>
              {/each}
            </ul>
          {/if}
          <h3>{tr(lang, 'suggestions')}</h3>
          {#each cat.suggestions as sg (sg.template_id)}
            <article class="suggestion">
              <div>
                <strong>{sg.title}</strong>
                {#if sg.safety_related}<span class="tag">⚠ {tr(lang, 'safety_related').split(' (')[0]}</span>{/if}
                <p class="muted">{sg.scenario}</p>
              </div>
              {#if sg.adopted}
                <span class="ok">✓ {tr(lang, 'adopted')}</span>
              {:else}
                <button disabled={busy} onclick={() => adopt(sg.template_id)} data-testid="adopt-{sg.template_id}">{tr(lang, 'adopt')}</button>
              {/if}
            </article>
          {:else}
            <p class="muted">{tr(lang, 'no_suggestions')}</p>
          {/each}
        </details>
      {/if}
    {/each}
  {/if}
</section>

<style>
  h1 {
    font-size: 1.3rem;
    margin-top: 0;
  }
  select {
    max-width: 32rem;
    display: block;
    margin-bottom: 1rem;
  }
  details {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    margin-bottom: 0.5rem;
    padding: 0.4rem 0.75rem;
  }
  details.done summary strong::after {
    content: ' ✓';
    color: var(--ok);
  }
  summary {
    cursor: pointer;
  }
  h3 {
    font-size: 0.95rem;
    margin: 0.6rem 0 0.3rem;
  }
  .suggestion {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
    border-top: 1px solid var(--border);
    padding: 0.5rem 0;
  }
  .suggestion p {
    margin: 0.2rem 0 0;
  }
  .tag {
    margin-left: 0.5rem;
    color: var(--warning);
    font-size: 0.9em;
  }
  .rowlink {
    border: none;
    background: none;
    padding: 0;
    color: var(--accent);
    font-weight: 600;
  }
</style>
