<script lang="ts">
  import { SvelteFlowProvider } from '@xyflow/svelte'
  import '@xyflow/svelte/dist/style.css'
  import { api, download } from '../../api'
  import { tr } from '../../i18n'
  import { app } from '../../state.svelte'
  import type { ElementType } from '../../types'
  import ObjectForm from '../ObjectForm.svelte'
  import Canvas from './Canvas.svelte'

  let types = $state<ElementType[]>([])
  let flowType = $state('')
  let configuration = $state('')
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
    <h2>{tr(lang, 'palette')}</h2>
    <p class="muted">{tr(lang, 'palette_help')}</p>
    <ul>
      {#each elementTypes as t (t.id)}
        <li
          draggable="true"
          ondragstart={(e) => e.dataTransfer?.setData('application/x-threatwright-type', t.id)}
          data-testid="palette-{t.id}"
        >
          <span class="kind kind-{t.kind}"></span>{t.name[lang]}
        </li>
      {/each}
    </ul>
  </aside>

  <div class="main">
    <div class="toolbar">
      <label>
        {tr(lang, 'flow_type')}
        <select bind:value={flowType} data-testid="flow-type">
          <option value="">{tr(lang, 'generic_flow')}</option>
          {#each flowTypes as t}<option value={t.id}>{t.name[lang]}</option>{/each}
        </select>
      </label>
      <label>
        {tr(lang, 'configurations')}
        <select bind:value={configuration}>
          <option value="">{tr(lang, 'all_configurations')}</option>
          {#each app.model?.meta.configurations ?? [] as c}<option value={c.id}>{c.id} {c.title}</option>{/each}
        </select>
      </label>
      <span class="spacer"></span>
      <button onclick={() => canvas?.autoLayout()} data-testid="auto-layout">{tr(lang, 'auto_layout')}</button>
      <button onclick={exportSvg}>{tr(lang, 'export_svg')}</button>
    </div>
    <SvelteFlowProvider>
      <Canvas bind:this={canvas} {flowType} {configuration} onselect={select} />
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
  .palette li {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    padding: 0.3rem 0.5rem;
    cursor: grab;
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }
  .kind {
    width: 14px;
    height: 10px;
    border: 1.5px solid var(--text);
    border-radius: 2px;
    flex: none;
  }
  .kind-process {
    border-radius: 6px;
  }
  .kind-external {
    border-width: 2.5px;
    border-radius: 0;
  }
  .kind-datastore {
    border-left: none;
    border-right: none;
    border-radius: 0;
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
