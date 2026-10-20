<script lang="ts">
  import { SvelteFlowProvider } from '@xyflow/svelte'
  import '@xyflow/svelte/dist/style.css'
  import { api, download } from '../../api'
  import { tr } from '../../i18n'
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
  let selected = $state<{ collection: 'elements' | 'flows'; id: string } | null>(null)
  let canvas: Canvas | undefined = $state()
  const lang = $derived(app.lang)
  const elementTypes = $derived(types.filter((t) => t.kind !== 'flow'))
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
    <ul>
      {#each elementTypes as t (t.id)}
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
  </aside>

  <div class="main">
    <div class="toolbar">
      <label>
        <span>{tr(lang, 'flow_type')} <Info term="flow" /></span>
        <select bind:value={flowType} data-testid="flow-type">
          <option value="">{tr(lang, 'generic_flow')}</option>
          {#each flowTypes as t}<option value={t.id}>{t.name[lang]}</option>{/each}
        </select>
      </label>
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
      <button onclick={() => canvas?.autoLayout()} data-testid="auto-layout">{tr(lang, 'auto_layout')}</button>
      <button onclick={exportSvg}>{tr(lang, 'export_svg')}</button>
    </div>
    <SvelteFlowProvider>
      <Canvas bind:this={canvas} {flowType} {configuration} types={elementTypes} onselect={select} />
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
  .toolbar select {
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
