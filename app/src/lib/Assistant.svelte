<script lang="ts">
  import { api } from '../api'
  import { label, tr } from '../i18n'
  import { app } from '../state.svelte'
  import { STRIDE_QUESTIONS } from '../glossary'
  import type { Category, ModelPayload } from '../types'
  import Info from './Info.svelte'

  let { target }: { target: string | null } = $props()

  let categories = $state<Record<string, Category> | null>(null)
  let busy = $state(false)
  // which categories are open: decided once per target, then by the user (adopting must not collapse)
  let open = $state<Record<string, boolean>>({})
  let openFor: string | null = null
  let chosen = $state<string[]>([]) // template ids selected for adoption
  const lang = $derived(app.lang)
  const targets = $derived([...app.objects('elements'), ...app.objects('flows')])
  const threatTitle = (id: string) => app.objects('threats').find((t) => t.id === id)?.title ?? ''
  const untypedFlow = $derived(!!app.objects('flows').find((f) => f.id === target && !f.library_ref))
  // every not yet adopted suggestion of the relevant categories (a template may span several)
  const pendingAll = $derived([
    ...new Set(
      Object.values(categories ?? {})
        .filter((c) => c.relevant)
        .flatMap((c) => c.suggestions.filter((s) => !s.adopted).map((s) => s.template_id)),
    ),
  ])

  async function load() {
    const t = target
    const cats = t
      ? (await api<{ categories: Record<string, Category> }>('GET', `/models/${app.modelName}/assistant/${t}`)).categories
      : null
    if (t !== target) return // the user switched targets meanwhile
    categories = cats
    if (t !== openFor) {
      openFor = t
      chosen = []
      open = Object.fromEntries(Object.entries(cats ?? {}).map(([s, c]) => [s, c.relevant && c.existing.length === 0]))
    }
  }

  $effect(() => {
    void target
    void app.model
    load()
  })

  function choose(template: string, on: boolean) {
    chosen = on ? [...new Set([...chosen, template])] : chosen.filter((x) => x !== template)
  }

  async function adopt(templates: string[]) {
    busy = true
    try {
      let model: ModelPayload | undefined
      for (const template of templates) {
        const r = await api<{ id: string; model: ModelPayload }>(
          'POST',
          `/models/${app.modelName}/assistant/${target}`,
          { template },
        )
        model = r.model
      }
      await app.afterChange(model)
      chosen = chosen.filter((x) => !templates.includes(x))
    } finally {
      busy = false
    }
  }

</script>

<section>
  <h1>{tr(lang, 'assistant')} <Info term="stride" /></h1>
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
    {#if untypedFlow}<p class="warning" data-testid="assistant-untyped-flow">{tr(lang, 'flow_needs_type')}</p>{/if}
    {#if pendingAll.length}
      <div class="bulk">
        <button onclick={() => (chosen = [...pendingAll])} data-testid="select-all-suggestions">
          {tr(lang, 'select_all_suggestions')} ({pendingAll.length})
        </button>
        <span class="muted">{tr(lang, 'select_all_help')}</span>
      </div>
    {/if}
    {#each Object.entries(categories) as [s, cat] (s)}
      {#if cat.relevant || cat.existing.length}
        <details
          open={open[s] ?? false}
          ontoggle={(e) => (open[s] = e.currentTarget.open)}
          class:done={cat.existing.length > 0 || !!cat.not_relevant}
        >
          <summary>
            <strong>{s}</strong> {label(lang, s)}
            <span class="muted">
              · {cat.existing.length} {tr(lang, 'existing_short')} · {cat.suggestions.length} {tr(lang, 'suggestions_short')}
            </span>
            {#if cat.not_relevant}<span class="muted">· {tr(lang, 'not_relevant')}</span>{/if}
            <span class="question">{STRIDE_QUESTIONS[lang][s]}</span>
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
              {#if !sg.adopted}
                <input
                  type="checkbox"
                  checked={chosen.includes(sg.template_id)}
                  onchange={(e) => choose(sg.template_id, e.currentTarget.checked)}
                  aria-label="{tr(lang, 'select')}: {sg.title}"
                  data-testid="choose-{sg.template_id}"
                />
              {/if}
              <div class="text">
                <strong>{sg.title}</strong>
                {#if sg.safety_related}<span class="tag">⚠ {tr(lang, 'safety_related').split(' (')[0]}</span>{/if}
                <p class="muted">{sg.scenario}</p>
              </div>
              {#if sg.adopted}
                <span class="ok">✓ {tr(lang, 'adopted')}</span>
              {:else}
                <button disabled={busy} onclick={() => adopt([sg.template_id])} data-testid="adopt-{sg.template_id}">{tr(lang, 'adopt')}</button>
              {/if}
            </article>
          {:else}
            <p class="muted">{tr(lang, 'no_suggestions')}</p>
          {/each}
        </details>
      {/if}
    {/each}
  {/if}

  {#if chosen.length}
    <div class="actionbar" data-testid="adopt-bar">
      <span><strong>{chosen.length}</strong> {tr(lang, 'selected_n')}</span>
      <button class="primary" disabled={busy} onclick={() => adopt([...chosen])} data-testid="adopt-chosen">
        {tr(lang, 'adopt_selected')}
      </button>
      <button class="link" onclick={() => (chosen = [])}>{tr(lang, 'clear_selection')}</button>
    </div>
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
  .question {
    display: block;
    margin: 0.15rem 0 0 1.1rem;
    color: var(--muted);
    font-style: italic;
  }
  h3 {
    font-size: 0.95rem;
    margin: 0.6rem 0 0.3rem;
  }
  .suggestion {
    display: flex;
    gap: 0.75rem;
    align-items: start;
    border-top: 1px solid var(--border);
    padding: 0.5rem 0;
  }
  .suggestion input {
    width: auto;
    margin-top: 0.25rem;
  }
  .suggestion .text {
    flex: 1;
  }
  .bulk {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
  }
  .actionbar {
    position: sticky;
    bottom: 0.75rem;
    display: flex;
    gap: 0.9rem;
    align-items: center;
    width: fit-content;
    margin: 0.75rem 0 0 auto;
    padding: 0.55rem 0.9rem;
    background: var(--surface);
    border: 1px solid var(--accent);
    border-radius: var(--radius);
    box-shadow: 0 8px 24px rgb(0 0 0 / 0.18);
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
