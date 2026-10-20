<script lang="ts">
  import { SvelteFlowProvider } from '@xyflow/svelte'
  import Search from '@lucide/svelte/icons/search'
  import StickyNote from '@lucide/svelte/icons/sticky-note'
  import '@xyflow/svelte/dist/style.css'
  import { api, download } from '../../api'
  import { tr } from '../../i18n'
  import { CATEGORIES } from '../../setup-text'
  import { app } from '../../state.svelte'
  import type { ElementType } from '../../types'
  import { iconFor } from '../icons'
  import Info from '../Info.svelte'
  import ObjectForm from '../ObjectForm.svelte'
  import Canvas from './Canvas.svelte'

  let types = $state<ElementType[]>([])
  let flowType = $state('')
  let configuration = $state<string[]>([]) // selected variants; empty = all
  const configs = $derived(app.model?.meta.configurations ?? [])
  // elements with variants of which none is selected; unassigned ones belong to every variant
  const hiddenCount = $derived(
    configuration.length
      ? app.objects('elements').filter((e) => e.configurations?.length && !e.configurations.some((c: string) => configuration.includes(c))).length
      : 0,
  )
  function toggleConfig(id: string, on: boolean) {
    configuration = on ? [...configuration, id] : configuration.filter((c) => c !== id)
  }
  let flowFilter = $state<string[]>([]) // connection types ('' = untyped); empty = all
  // types that occur in the model, untyped last
  const protocols = $derived(
    [...new Set(app.objects('flows').map((f) => (f.protocol ?? '') as string))].sort((a, b) => (!a ? 1 : !b ? -1 : a.localeCompare(b))),
  )
  function toggleFlowType(p: string, on: boolean) {
    flowFilter = on ? [...flowFilter, p] : flowFilter.filter((x) => x !== p)
  }
  let search = $state('')
  let hits = $state(0)
  const SNAP_KEY = 'tw-snap'
  let snap = $state(readSnap())
  function readSnap() {
    try {
      return localStorage.getItem(SNAP_KEY) === '1'
    } catch {
      return false
    }
  }
  $effect(() => {
    try {
      localStorage.setItem(SNAP_KEY, snap ? '1' : '0')
    } catch {
      /* storage unavailable */
    }
  })
  let selected = $state<{ collection: 'elements' | 'flows'; id: string } | null>(null)
  let canvas: Canvas | undefined = $state()
  const lang = $derived(app.lang)
  const elementTypes = $derived(types.filter((t) => t.kind !== 'flow'))
  let paletteFilter = $state('')
  // grouped like the setup wizard; the search also looks at the description
  const paletteGroups = $derived.by(() => {
    const f = paletteFilter.trim().toLowerCase()
    const shown = elementTypes.filter(
      (t) => !f || [t.name[lang], t.id, t.description?.[lang]].some((v) => v?.toLowerCase().includes(f)),
    )
    const order = Object.keys(CATEGORIES[lang])
    const by: Record<string, ElementType[]> = {}
    for (const t of shown) (by[t.category && order.includes(t.category) ? t.category : 'other'] ??= []).push(t)
    return order.filter((c) => by[c]).map((c) => [c, by[c]] as const)
  })
  const flowTypes = $derived(types.filter((t) => t.kind === 'flow'))
  const current = $derived(selected ? app.objects(selected.collection).find((o) => o.id === selected!.id) : null)

  $effect(() => {
    api<{ elements: ElementType[] }>('GET', '/library').then((r) => (types = r.elements))
  })

  function select(collection: 'elements' | 'flows', id: string | null) {
    selected = id ? { collection, id } : null
  }

  const exportSvg = () => download(`/models/${app.modelName}/diagram.svg`, `${app.modelName}-diagram.svg`)
</script>

<section class="diagram">
  <!-- svelte-ignore a11y_no_noninteractive_tabindex (scrollable region must be keyboard reachable) -->
  <aside class="palette" aria-label={tr(lang, 'palette')} tabindex="0">
    <h2>{tr(lang, 'palette')} <Info term="palette" /></h2>
    <p class="muted">{tr(lang, 'palette_help')}</p>
    <label class="new-flow">
      <span>{tr(lang, 'flow_type')} <Info term="flow" /></span>
      <select bind:value={flowType} data-testid="flow-type">
        <option value="">{tr(lang, 'generic_flow')}</option>
        {#each flowTypes as t}<option value={t.id}>{t.name[lang]}</option>{/each}
      </select>
    </label>
    <input
      type="search"
      class="palette-search"
      bind:value={paletteFilter}
      placeholder={tr(lang, 'palette_search')}
      aria-label={tr(lang, 'palette_search')}
      onkeydown={(e) => {
        // Enter adds the first match
        const first = paletteGroups[0]?.[1][0]
        if (e.key === 'Enter' && first) canvas?.addElement(first.id)
      }}
      data-testid="palette-search"
    />
    {#each paletteGroups as [cat, list] (cat)}
      <h3>{CATEGORIES[lang][cat]}</h3>
      <ul>
        {#each list as t (t.id)}
          {@const Icon = iconFor(t.icon, t.kind)}
          <li>
            <button
              draggable="true"
              ondragstart={(e) => e.dataTransfer?.setData('application/x-threatwright-type', t.id)}
              onclick={() => canvas?.addElement(t.id)}
              title={tr(lang, 'palette_add')}
              data-testid="palette-{t.id}"
            >
              <span class="kind kind-{t.kind}"><Icon size={16} strokeWidth={1.75} aria-hidden="true" /></span>{t.name[lang]}
            </button>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="muted">{elementTypes.length ? tr(lang, 'palette_no_match') : ''}</p>
    {/each}
    <p class="muted small">{tr(lang, 'multi_select_help')}</p>
  </aside>

  <div class="main">
    <div class="toolbar">
      <label class="search">
        <span>{tr(lang, 'search')}</span>
        <span class="field">
          <Search size={14} aria-hidden="true" />
          <input
            type="search"
            bind:value={search}
            placeholder={tr(lang, 'search_placeholder')}
            title={tr(lang, 'search_help')}
            onkeydown={(e) => e.key === 'Enter' && canvas?.showHits()}
            data-testid="diagram-search"
          />
          {#if search.trim()}<span class="muted hits" data-testid="search-hits" aria-live="polite">{hits} {tr(lang, 'search_hits')}</span>{/if}
        </span>
      </label>
      <div class="filter">
        <span>{tr(lang, 'flow_filter')}</span>
        <details class="dropdown" data-testid="flow-filter">
          <summary>
            {flowFilter.length ? flowFilter.map((p) => p || tr(lang, 'generic_flow')).join(', ') : tr(lang, 'all_flow_types')}
          </summary>
          <div class="menu">
            {#each protocols as p (p)}
              <label class="check">
                <input
                  type="checkbox"
                  checked={flowFilter.includes(p)}
                  onchange={(e) => toggleFlowType(p, e.currentTarget.checked)}
                  data-testid="flow-filter-{p || 'generic'}"
                />
                {p || tr(lang, 'generic_flow')}
              </label>
            {:else}
              <p class="muted">{tr(lang, 'no_flows')}</p>
            {/each}
            {#if flowFilter.length}
              <button type="button" class="link" onclick={() => (flowFilter = [])}>{tr(lang, 'show_all')}</button>
            {/if}
            <p class="muted small">{tr(lang, 'flow_filter_help')}</p>
          </div>
        </details>
      </div>
      <div class="filter">
        <span>{tr(lang, 'configurations')} <Info term="configurations" /></span>
        <details class="dropdown" data-testid="config-filter">
          <summary>
            {configuration.length
              ? configs.filter((c) => configuration.includes(c.id)).map((c) => c.title || c.id).join(', ')
              : tr(lang, 'all_configurations')}
            {#if hiddenCount}<span class="muted">· {hiddenCount} {tr(lang, 'hidden_count')}</span>{/if}
          </summary>
          <div class="menu">
            {#each configs as c (c.id)}
              <label class="check">
                <input
                  type="checkbox"
                  checked={configuration.includes(c.id)}
                  onchange={(e) => toggleConfig(c.id, e.currentTarget.checked)}
                  data-testid="config-{c.id}"
                />
                {c.id} {c.title}
              </label>
            {:else}
              <p class="muted">{tr(lang, 'no_configurations')}</p>
            {/each}
            {#if configuration.length}
              <button type="button" class="link" onclick={() => (configuration = [])}>{tr(lang, 'show_all')}</button>
            {/if}
            <p class="muted small">{tr(lang, 'config_filter_help')}</p>
          </div>
        </details>
      </div>
      <span class="spacer"></span>
      <button onclick={() => canvas?.addNote()} title={tr(lang, 'add_note_help')} data-testid="add-note">
        <StickyNote size={14} aria-hidden="true" /> {tr(lang, 'add_note')}
      </button>
      <label class="check snap" title={tr(lang, 'snap_grid_help')}>
        <input type="checkbox" bind:checked={snap} data-testid="snap-grid" />
        {tr(lang, 'snap_grid')}
      </label>
      <button onclick={() => canvas?.autoLayout()} data-testid="auto-layout">{tr(lang, 'auto_layout')}</button>
      <button onclick={exportSvg}>{tr(lang, 'export_svg')}</button>
    </div>
    <SvelteFlowProvider>
      <Canvas
        bind:this={canvas}
        {flowType}
        {configuration}
        {flowFilter}
        {search}
        {snap}
        types={elementTypes}
        onselect={select}
        onsearchhits={(n) => (hits = n)}
      />
    </SvelteFlowProvider>
  </div>

  {#if current && selected}
    <aside class="panel">
      <button class="primary assist" onclick={() => (app.view = { kind: 'assistant', target: current.id })} data-testid="open-assistant">
        {tr(lang, 'assistant')} →
      </button>
      {#key current.id}
        <ObjectForm collection={selected.collection} source={current} onsaved={() => {}} onclose={() => (selected = null)} />
      {/key}
    </aside>
  {/if}
</section>

<style>
  .diagram {
    display: grid;
    grid-template-columns: 13rem minmax(0, 1fr) auto;
    gap: 0.75rem;
    height: calc(100vh - 6rem);
  }
  .palette {
    overflow: auto;
  }
  .palette h2 {
    font-size: 1rem;
    margin: 0;
  }
  .new-flow {
    display: grid;
    gap: 0.15rem;
    font-size: 0.9em;
    margin-bottom: 0.25rem;
  }
  .palette .small {
    font-size: 0.85em;
  }
  .palette-search {
    width: 100%;
    margin: 0.25rem 0;
  }
  .palette h3 {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--muted);
    margin: 0.75rem 0 0;
  }
  .palette ul {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 0.25rem;
  }
  .palette button {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    padding: 0.3rem 0.5rem;
    cursor: grab;
    display: flex;
    gap: 0.5rem;
    align-items: center;
    text-align: left;
  }
  .palette button:hover {
    border-color: var(--accent);
  }
  .kind {
    display: grid;
    place-items: center;
    flex: none;
    color: var(--muted);
  }
  .main {
    display: grid;
    grid-template-rows: auto 1fr;
    gap: 0.5rem;
    min-width: 0;
  }
  .toolbar {
    display: flex;
    gap: 0.75rem;
    align-items: end;
    flex-wrap: wrap;
  }
  .toolbar label {
    display: grid;
    gap: 0.15rem;
    font-size: 0.9em;
  }
  .search .field {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0 0.5rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  .search .field:focus-within {
    outline: 2px solid var(--focus);
  }
  .search input {
    border: none;
    outline: none;
    background: none;
    padding: 0.35rem 0;
    width: 13rem;
  }
  .hits {
    white-space: nowrap;
    font-size: 0.9em;
  }
  .toolbar > button {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }
  .toolbar .snap {
    display: flex;
    gap: 0.35rem;
    align-items: center;
    padding: 0.4rem 0;
  }
  .toolbar .snap input {
    width: auto;
  }
  .filter {
    display: grid;
    gap: 0.15rem;
    font-size: 0.9em;
    position: relative;
  }
  .dropdown summary {
    list-style: none;
    cursor: pointer;
    min-width: 12rem;
    padding: 0.35rem 1.8rem 0.35rem 0.6rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    position: relative;
  }
  .dropdown summary::after {
    content: '';
    position: absolute;
    right: 0.7rem;
    top: 50%;
    width: 0.4rem;
    height: 0.4rem;
    border-right: 1.5px solid currentColor;
    border-bottom: 1.5px solid currentColor;
    transform: translateY(-70%) rotate(45deg);
  }
  .dropdown[open] summary {
    border-color: var(--accent);
  }
  .menu {
    position: absolute;
    z-index: 10;
    margin-top: 0.25rem;
    min-width: 16rem;
    max-width: 24rem;
    display: grid;
    gap: 0.35rem;
    padding: 0.6rem 0.75rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 8px 24px rgb(0 0 0 / 0.18);
  }
  .menu .check {
    display: flex;
    gap: 0.45rem;
    align-items: center;
  }
  .menu .check input {
    width: auto;
  }
  .menu .small {
    margin: 0;
    font-size: 0.85em;
  }
  .spacer {
    flex: 1;
  }
  .panel {
    width: 26rem;
    overflow: auto;
  }
  .assist {
    margin-bottom: 0.5rem;
  }
</style>
