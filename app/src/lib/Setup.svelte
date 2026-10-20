<script lang="ts">
  // Guided initial setup of a model: product, zones, components, connections, assets, threats.
  // Every step works on the regular model through the existing API (undo and save as usual).
  import { api, ApiError } from '../api'
  import { label, tr } from '../i18n'
  import { ASSET_CLASSES, assetClassLabel, CATEGORIES, SETUP } from '../setup-text'
  import { app } from '../state.svelte'
  import type { Category, ElementType, ModelPayload, Obj, ProjectInfo } from '../types'
  import { SvelteFlowProvider } from '@xyflow/svelte'
  import '@xyflow/svelte/dist/style.css'
  import Canvas from './diagram/Canvas.svelte'
  import Info from './Info.svelte'
  import MultiSelect from './MultiSelect.svelte'

  let { step }: { step: number } = $props()

  const lang = $derived(app.lang)
  const t = $derived(SETUP[lang])
  const STEPS = ['s_product', 's_zones', 's_elements', 's_flows', 's_assets', 's_threats', 's_finish'] as const
  const indicators = ['interface', 'access', 'user'] as const

  let error = $state('')
  let busy = $state(false)
  let types = $state<ElementType[]>([])
  let meta = $state<Record<string, any>>({})

  const zones = $derived((app.model?.meta.zones ?? []) as { id: string; title: string; environment: Record<string, string | null> }[])
  const elements = $derived(app.objects('elements'))
  const flows = $derived(app.objects('flows'))
  const assets = $derived(app.objects('assets'))
  const threats = $derived(app.objects('threats'))
  const elementTypes = $derived(types.filter((x) => x.kind !== 'flow'))
  const flowTypes = $derived(types.filter((x) => x.kind === 'flow'))
  const title = (id: string) => [...elements, ...flows, ...assets].find((o) => o.id === id)?.title ?? id

  $effect(() => {
    api<{ elements: ElementType[] }>('GET', '/library').then((r) => (types = r.elements)).catch(() => (types = []))
  })

  // meta draft for the product and zone steps; reset when the model changes (e.g. undo)
  $effect(() => {
    meta = structuredClone($state.snapshot(app.model?.meta ?? {})) as Record<string, any>
  })

  async function guard(fn: () => Promise<void>) {
    error = ''
    busy = true
    try {
      await fn()
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e)
    } finally {
      busy = false
    }
  }

  const path = (rest: string) => `/models/${app.modelName}${rest}`

  async function saveMeta() {
    const model = await api<ModelPayload>('PUT', path('/meta'), $state.snapshot(meta))
    await app.afterChange(model)
  }

  async function go(n: number) {
    // product and zones are edited as a draft: apply before leaving the step
    if (step === 1 || step === 2) {
      error = ''
      try {
        await saveMeta()
      } catch (e) {
        error = e instanceof ApiError ? e.message : String(e)
        return
      }
    }
    app.view = { kind: 'setup', step: n }
  }

  async function createModel() {
    await guard(async () => {
      const info = await api<ProjectInfo>('POST', '/models', { name: 'main', title: lang === 'de' ? 'Hauptmodell' : 'Main model' })
      await app.loadProject(info)
      app.view = { kind: 'setup', step: 1 }
    })
  }

  // --- step 3: components ----------------------------------------------------------
  let filter = $state('')
  let picked = $state<ElementType | null>(null)
  let newTitle = $state('')
  let newZone = $state('')

  const groups = $derived.by(() => {
    const f = filter.trim().toLowerCase()
    const shown = elementTypes.filter((x) => !f || x.name[lang].toLowerCase().includes(f))
    const order = Object.keys(CATEGORIES[lang])
    const by: Record<string, ElementType[]> = {}
    for (const x of shown) (by[x.category && order.includes(x.category) ? x.category : 'other'] ??= []).push(x)
    return order.filter((c) => by[c]).map((c) => [c, by[c]] as const)
  })

  function suggestedZone(x: ElementType): string {
    return zones.find((z) => z.environment?.interface === x.environment?.interface)?.id ?? zones[0]?.id ?? ''
  }

  function pick(x: ElementType) {
    picked = x
    newTitle = x.name[lang]
    newZone = suggestedZone(x)
  }

  async function addElement() {
    if (!picked) return
    const type = picked
    await guard(async () => {
      // place new elements in one column per zone so the diagram starts readable
      const column = Math.max(0, zones.findIndex((z) => z.id === newZone))
      const row = elements.filter((e) => e.zone === newZone).length
      const r = await api<{ id: string; model: ModelPayload }>('POST', path('/add/element'), {
        type: type.id,
        title: newTitle.trim() || type.name[lang],
        zone: newZone || null,
        x: 40 + column * 260,
        y: 40 + row * 130,
      })
      await app.afterChange(r.model)
      if (picked === type) picked = null // keep a type picked meanwhile
    })
  }

  async function update(collection: 'elements' | 'assets' | 'threats', obj: Obj, change: Partial<Obj>) {
    await guard(async () => {
      const r = await api<{ model: ModelPayload }>('PUT', path(`/${collection}/${obj.id}`), {
        ...$state.snapshot(obj),
        ...change,
      })
      await app.afterChange(r.model)
    })
  }

  async function remove(collection: 'elements' | 'flows' | 'assets', id: string) {
    await guard(async () => {
      await app.afterChange(await api<ModelPayload>('DELETE', path(`/${collection}/${id}`)))
    })
  }

  // --- step 4: connections -------------------------------------------------------------
  let source = $state('')
  let target = $state('')
  let flowType = $state('')
  const zoneOf = (id: string) => elements.find((e) => e.id === id)?.zone ?? null

  async function addFlow() {
    await guard(async () => {
      const r = await api<{ id: string; model: ModelPayload }>('POST', path('/add/flow'), {
        source,
        target,
        type: flowType || null,
      })
      await app.afterChange(r.model)
      target = ''
    })
  }

  // --- step 5: assets ---------------------------------------------------------------------
  let assetTitle = $state('')
  let assetClass = $state('')
  const classes = $derived(Object.keys(app.method?.asset_classes ?? {}))
  const assetOptions = $derived(
    assets.filter((a) => !String(a.asset_class).startsWith('Security.')).map((a) => ({ value: a.id, label: `${a.id} ${a.title}` })),
  )

  async function addAsset() {
    await guard(async () => {
      const r = await api<{ model: ModelPayload }>('POST', path('/assets'), { title: assetTitle, asset_class: assetClass })
      await app.afterChange(r.model)
      assetTitle = ''
    })
  }

  function impacts(id: string): string {
    const i = app.model?.asset_impacts[id]
    return i ? (['C', 'I', 'A'] as const).map((d) => i[d] ?? '–').join(' / ') : ''
  }

  // --- step 6: threats ---------------------------------------------------------------------
  let suggestions = $state<Record<string, Record<string, Category>>>({})
  let chosen = $state<Record<string, string[]>>({})
  const targets = $derived([...elements, ...flows])
  const openCyber = $derived(threats.filter((x) => x.cyber_cause == null && x.status !== 'rejected'))

  async function loadSuggestions(id: string) {
    const r = await api<{ categories: Record<string, Category> }>('GET', path(`/assistant/${id}`))
    suggestions[id] = r.categories
  }

  const TOP = 5 // shown per target before "more"; a long list invites adopting everything
  let expanded = $state<Record<string, boolean>>({})

  function suggestionList(id: string) {
    const seen = new Set<string>()
    const out: { template_id: string; title: string; scenario: string; adopted: boolean; stride: string; impact: number }[] = []
    for (const [s, cat] of Object.entries(suggestions[id] ?? {})) {
      if (!cat.relevant) continue
      for (const sg of cat.suggestions) {
        if (seen.has(sg.template_id)) continue
        seen.add(sg.template_id)
        out.push({ template_id: sg.template_id, title: sg.title, scenario: sg.scenario, adopted: sg.adopted, stride: s, impact: sg.impact ?? 0 })
      }
    }
    // ponytail: "relevance" = template impact; replace with a real score once libraries carry one
    return out.sort((a, b) => b.impact - a.impact)
  }

  async function adopt(id: string) {
    const templates = chosen[id] ?? []
    await guard(async () => {
      let model: ModelPayload | undefined
      for (const template of templates) {
        model = (await api<{ model: ModelPayload }>('POST', path(`/assistant/${id}`), { template })).model
      }
      await app.afterChange(model)
      chosen[id] = []
      await loadSuggestions(id)
    })
  }

  // --- step 7: finish ------------------------------------------------------------------------
  const errors = $derived(app.issues.filter((i) => i.severity === 'error').length)
  const checks = $derived([
    [t.c_description, !!app.model?.meta.description?.trim()],
    [t.c_zones, zones.length > 0 && zones.every((z) => indicators.every((i) => z.environment?.[i]))],
    [t.c_elements, elements.length > 0, elements.length],
    [t.c_flows, flows.length > 0, flows.length],
    [t.c_assets, assets.length > 0 && assets.every((a) => a.asset_class), assets.length],
    [t.c_threats, threats.length > 0, threats.length],
    [t.c_cyber, threats.length > 0 && openCyber.length === 0],
  ] as [string, boolean, number?][])
</script>

{#snippet preview(type: string)}
  <h3>{t.preview}</h3>
  <p class="muted small">{t.preview_help}</p>
  <div class="preview" data-testid="setup-preview">
    <SvelteFlowProvider>
      <Canvas flowType={type} configuration="" types={elementTypes} onselect={() => {}} />
    </SvelteFlowProvider>
  </div>
{/snippet}

<section class="setup" data-testid="setup">
  <h1>{t.title}</h1>

  {#if step > 0}
    <ol class="steps" aria-label={t.title}>
      {#each STEPS as s, n}
        <li aria-current={step === n + 1 ? 'step' : undefined}>
          <button class="link" onclick={() => go(n + 1)} disabled={busy || !app.model}>{n + 1}. {t[s]}</button>
        </li>
      {/each}
    </ol>
  {/if}

  {#if error}<pre class="error" role="alert">{error}</pre>{/if}

  {#if step === 0}
    <div class="card">
      <h2>{t.intro_title}</h2>
      <p>{t.intro_text}</p>
      <ol>
        {#each STEPS as s}<li>{t[s]}</li>{/each}
      </ol>
      <p class="muted">{t.intro_save} {t.intro_time}</p>
      {#if !app.model}
        <p>{t.no_model}</p>
        <button class="primary" onclick={createModel} disabled={busy}>{t.create_model}</button>
      {:else}
        <button class="primary" onclick={() => go(1)} data-testid="setup-start">{t.start}</button>
      {/if}
    </div>
  {:else if step === 1}
    <h2>{t.s_product}</h2>
    <p>{t.product_text}</p>
    <details class="hint">
      <summary>{t.product_questions}</summary>
      <ul>{#each t.product_q as q}<li>{q}</li>{/each}</ul>
    </details>
    <label for="setup-title">{t.model_title}</label>
    <input id="setup-title" bind:value={meta.title} data-testid="setup-title" />
    <label for="setup-description">{t.description}</label>
    <textarea id="setup-description" rows="7" bind:value={meta.description} placeholder={t.description_placeholder} data-testid="setup-description"></textarea>
    <h3>{t.configurations} <Info term="configurations" /></h3>
    <p class="muted">{t.configurations_help}</p>
    {#each meta.configurations ?? [] as c, n}
      <div class="row">
        <input bind:value={c.id} aria-label="ID" class="short" />
        <input bind:value={c.title} aria-label={t.configurations} />
        <button onclick={() => meta.configurations.splice(n, 1)} aria-label={t.remove}>×</button>
      </div>
    {/each}
    <button
      onclick={() => {
        const list = meta.configurations ?? []
        let n = list.length + 1
        while (list.some((c: { id: string }) => c.id === `K-${n}`)) n++
        meta.configurations = [...list, { id: `K-${n}`, title: '' }]
      }}>{t.add_configuration}</button
    >
  {:else if step === 2}
    <h2>{t.s_zones} <Info term="zone" /></h2>
    <p>{t.zones_text}</p>
    <p class="muted">{t.zones_hint}</p>
    {#each meta.zones ?? [] as zone, n}
      <fieldset class="card zone" data-testid="setup-zone-{zone.id}">
        <legend>{zone.id}</legend>
        <label for="zone-title-{n}">{t.zone_title}</label>
        <div class="row">
          <input id="zone-title-{n}" bind:value={zone.title} />
          <button onclick={() => meta.zones.splice(n, 1)} aria-label={t.remove}>×</button>
        </div>
        <div class="indicators">
          {#each indicators as i}
            {@const values = app.method?.[i].values ?? {}}
            {@const current = zone.environment?.[i] ?? ''}
            <div>
              <label for="zone-{n}-{i}">{tr(lang, i)}</label>
              <select
                id="zone-{n}-{i}"
                value={current}
                onchange={(e) => (zone.environment = { ...(zone.environment ?? {}), [i]: e.currentTarget.value || null })}
                data-testid="zone-{zone.id}-{i}"
              >
                <option value="">{t.not_set}</option>
                {#each Object.entries(values) as [key, v]}<option value={key}>{v[lang]}</option>{/each}
              </select>
              {#if current && values[current]?.help}<p class="muted small">{values[current].help?.[lang]}</p>{/if}
            </div>
          {/each}
        </div>
      </fieldset>
    {/each}
    <button
      onclick={() => {
        const list = meta.zones ?? []
        let n = list.length + 1
        while (list.some((z: { id: string }) => z.id === `Z-${n}`)) n++
        meta.zones = [...list, { id: `Z-${n}`, title: '', environment: {} }]
      }}>{t.add_zone}</button
    >
  {:else if step === 3}
    <h2>{t.s_elements}</h2>
    <p>{t.elements_text}</p>
    <p class="muted">{t.elements_hint}</p>
    <div class="split">
      <div>
        <h3>{t.library} <Info term="palette" /></h3>
        <input type="search" bind:value={filter} placeholder={t.search} aria-label={t.search} />
        <!-- svelte-ignore a11y_no_noninteractive_tabindex (scrollable region must be keyboard reachable) -->
        <div class="scroll" tabindex="0" role="region" aria-label={t.library}>
          {#each groups as [cat, list]}
            <h4>{CATEGORIES[lang][cat]}</h4>
            <ul class="plain">
              {#each list as x (x.id)}
                <li>
                  <button class="pick" class:active={picked?.id === x.id} onclick={() => pick(x)} data-testid="setup-type-{x.id}">
                    <strong>{x.name[lang]}</strong> <span class="muted">· {label(lang, x.kind)}</span>
                  </button>
                </li>
              {/each}
            </ul>
          {/each}
        </div>
      </div>
      <div>
        {#if picked}
          <form class="card" onsubmit={(e) => { e.preventDefault(); addElement() }}>
            <h3>{picked.name[lang]}</h3>
            {#if picked.description}<p class="muted">{picked.description[lang]}</p>{/if}
            {#if picked.assets.length}
              <p class="small">{t.brings_assets}: {picked.assets.map((a) => a.title[lang]).join(', ')}</p>
            {/if}
            <label for="setup-el-title">{t.element_name}</label>
            <input id="setup-el-title" bind:value={newTitle} data-testid="setup-el-title" />
            <label for="setup-el-zone">{t.zone}</label>
            <select id="setup-el-zone" bind:value={newZone}>
              {#each zones as z}<option value={z.id}>{z.id} {z.title}</option>{/each}
            </select>
            <button class="primary" type="submit" disabled={busy} data-testid="setup-el-add">{t.add}</button>
          </form>
        {/if}
        <h3>{t.added} ({elements.length})</h3>
        {#each elements as e (e.id)}
          <div class="row item">
            <span class="grow"><strong>{e.id}</strong> {e.title}</span>
            <select
              value={e.zone ?? ''}
              aria-label="{t.zone} {e.id}"
              onchange={(ev) => update('elements', e, { zone: ev.currentTarget.value || null })}
            >
              {#each zones as z}<option value={z.id}>{z.title || z.id}</option>{/each}
            </select>
            <button onclick={() => remove('elements', e.id)} aria-label="{t.remove} {e.id}">×</button>
          </div>
        {:else}
          <p class="muted">{t.none_yet}</p>
        {/each}
      </div>
    </div>
    {#if elements.length}{@render preview('')}{/if}
  {:else if step === 4}
    <h2>{t.s_flows} <Info term="flow" /></h2>
    <p>{t.flows_text}</p>
    <p class="muted">{t.flows_hint}</p>
    {#if elements.length < 2}
      <p class="warning">{t.need_two}</p>
    {:else}
      <form class="card grid4" onsubmit={(e) => { e.preventDefault(); addFlow() }}>
        <div>
          <label for="setup-src">{t.source}</label>
          <!-- value + onchange, not bind: the target options depend on the source (bind lost the pick) -->
          <select
            id="setup-src"
            value={source}
            onchange={(e) => {
              source = e.currentTarget.value
              if (target === source) target = ''
            }}
            required
            data-testid="setup-flow-source"
          >
            <option value=""></option>
            {#each elements as e}<option value={e.id}>{e.id} {e.title}</option>{/each}
          </select>
        </div>
        <div>
          <label for="setup-tgt">{t.target}</label>
          <select id="setup-tgt" value={target} onchange={(e) => (target = e.currentTarget.value)} required data-testid="setup-flow-target">
            <option value=""></option>
            {#each elements.filter((e) => e.id !== source) as e}<option value={e.id}>{e.id} {e.title}</option>{/each}
          </select>
        </div>
        <div>
          <label for="setup-ftype">{t.flow_type}</label>
          <select id="setup-ftype" bind:value={flowType}>
            <option value="">{t.generic_flow}</option>
            {#each flowTypes as x}<option value={x.id}>{x.name[lang]}</option>{/each}
          </select>
        </div>
        <button class="primary" type="submit" disabled={busy || !source || !target} data-testid="setup-flow-add">{t.connect}</button>
      </form>
    {/if}
    <h3>{t.added} ({flows.length})</h3>
    {#each flows as f (f.id)}
      <div class="row item">
        <span class="grow">
          <strong>{f.id}</strong> {title(f.source)} → {title(f.target)}
          {#if f.protocol}<span class="muted">· {f.protocol}</span>{/if}
          {#if zoneOf(f.source) !== zoneOf(f.target)}<span class="tag">{t.crosses}</span>{/if}
        </span>
        <button onclick={() => remove('flows', f.id)} aria-label="{t.remove} {f.id}">×</button>
      </div>
    {:else}
      <p class="muted">{t.none_yet}</p>
    {/each}
    {#if elements.length}{@render preview(flowType)}{/if}
  {:else if step === 5}
    <h2>{t.s_assets} <Info term="asset_class" /></h2>
    <p>{t.assets_text}</p>
    <table>
      <thead>
        <tr><th>{t.asset_title}</th><th>{t.asset_class}</th><th>{t.impact}</th><th></th></tr>
      </thead>
      <tbody>
        {#each assets as a (a.id)}
          <tr>
            <td><strong>{a.id}</strong> {a.title}</td>
            <td>
              <select
                value={a.asset_class}
                aria-label="{t.asset_class} {a.id}"
                onchange={(e) => update('assets', a, { asset_class: e.currentTarget.value })}
              >
                <option value=""></option>
                {#each classes as c}<option value={c}>{assetClassLabel(lang, c)}</option>{/each}
              </select>
              <p class="muted small">{ASSET_CLASSES[lang][a.asset_class] ?? ''}</p>
              {#if String(a.asset_class).startsWith('Security.')}
                <span class="small" id="protects-{a.id}-label">{t.protects}</span>
                <MultiSelect
                  id="protects-{a.id}"
                  options={assetOptions}
                  value={a.protects ?? []}
                  onchange={(v) => update('assets', a, { protects: v })}
                />
                {#if !(a.protects ?? []).length}<p class="warning small">{t.protects_help}</p>{/if}
              {/if}
            </td>
            <td>{impacts(a.id)}</td>
            <td><button onclick={() => remove('assets', a.id)} aria-label="{t.remove} {a.id}">×</button></td>
          </tr>
        {/each}
      </tbody>
    </table>
    <form class="card grid3" onsubmit={(e) => { e.preventDefault(); addAsset() }}>
      <div>
        <label for="setup-asset-title">{t.asset_title}</label>
        <input id="setup-asset-title" bind:value={assetTitle} required data-testid="setup-asset-title" />
      </div>
      <div>
        <label for="setup-asset-class">{t.asset_class}</label>
        <select id="setup-asset-class" bind:value={assetClass} required data-testid="setup-asset-class">
          <option value=""></option>
          {#each classes as c}<option value={c}>{assetClassLabel(lang, c)}</option>{/each}
        </select>
        {#if assetClass}<p class="muted small">{ASSET_CLASSES[lang][assetClass] ?? ''}</p>{/if}
      </div>
      <button class="primary" type="submit" disabled={busy} data-testid="setup-asset-add">{t.add_asset}</button>
    </form>
  {:else if step === 6}
    <h2>{t.s_threats} <Info term="stride" /></h2>
    <p>{t.threats_text}</p>
    <p class="muted">{t.threats_cyber}</p>
    {#each targets as o (o.id)}
      <details
        class="card"
        ontoggle={(e) => {
          if (e.currentTarget.open && !suggestions[o.id]) loadSuggestions(o.id).catch(() => {})
        }}
        data-testid="setup-target-{o.id}"
      >
        <summary>
          <strong>{o.id}</strong> {o.title}
          {#if suggestions[o.id]}
            {@const all = suggestionList(o.id)}
            {#if all.length}<span class="muted small">· {all.filter((s) => s.adopted).length}/{all.length} {t.adopted_of}</span>{/if}
          {/if}
        </summary>
        {#if !suggestions[o.id]}
          <p class="muted">{t.loading}</p>
        {:else}
          {@const list = suggestionList(o.id)}
          {#if list.length === 0}
            <p class="muted">{o.source && !o.library_ref ? t.flow_needs_type : t.no_suggestions}</p>
          {:else}
            <ul class="plain">
              {#each expanded[o.id] ? list : list.slice(0, TOP) as s (s.template_id)}
                <li class="suggestion">
                  <label>
                    <input
                      type="checkbox"
                      disabled={s.adopted}
                      checked={s.adopted || (chosen[o.id] ?? []).includes(s.template_id)}
                      onchange={(e) => {
                        const cur = chosen[o.id] ?? []
                        chosen[o.id] = e.currentTarget.checked ? [...cur, s.template_id] : cur.filter((x) => x !== s.template_id)
                      }}
                      data-testid="setup-sg-{s.template_id}"
                    />
                    <span>
                      <strong>{s.stride}</strong> {s.title}
                      {#if s.adopted}<span class="ok">✓ {t.adopted}</span>{/if}
                      <span class="muted small block">{s.scenario}</span>
                    </span>
                  </label>
                </li>
              {/each}
            </ul>
            {#if !expanded[o.id] && list.length > TOP}
              <button class="link" onclick={() => (expanded[o.id] = true)} data-testid="setup-more-{o.id}">
                {t.more} ({list.length - TOP})
              </button>
            {/if}
            <button class="primary" disabled={busy || !(chosen[o.id] ?? []).length} onclick={() => adopt(o.id)} data-testid="setup-adopt-{o.id}">
              {t.adopt_selected} ({(chosen[o.id] ?? []).length})
            </button>
          {/if}
        {/if}
      </details>
    {/each}

    {#if openCyber.length}
      <h3>{t.open_cyber} <Info term="cyber_cause" /></h3>
      <p class="muted">{t.open_cyber_help}</p>
      {#each openCyber as x (x.id)}
        <div class="row item cyber" data-testid="setup-cyber-{x.id}">
          <span class="grow">
            <strong>{x.id}</strong> {x.title}
            {#if x.scenario}<span class="muted small block">{x.scenario}</span>{/if}
          </span>
          <button onclick={() => update('threats', x, { cyber_cause: true })} disabled={busy} data-testid="setup-cyber-yes-{x.id}">{t.yes}</button>
          <button onclick={() => (app.cyberCheck = x.id)}>{t.no}</button>
        </div>
      {/each}
    {/if}
  {:else}
    <h2>{t.s_finish}</h2>
    <p>{t.finish_text}</p>
    <h3>{t.checklist}</h3>
    <ul class="plain checks" data-testid="setup-checks">
      {#each checks as [text, ok, count]}
        <li><span class={ok ? 'ok' : 'warning'}>{ok ? '✓' : '•'}</span> {text}{count != null ? `: ${count}` : ''}</li>
      {/each}
      <li>
        <span class={errors ? 'error' : 'ok'}>{errors ? '•' : '✓'}</span> {t.c_errors}: {errors}
        {#if errors}<button class="link" onclick={() => (app.view = { kind: 'validation' })} data-testid="setup-show-errors">{t.show_errors}</button>{/if}
      </li>
    </ul>
    <h3>{t.next_steps}</h3>
    <ol>
      <li>{t.n_assess}</li>
      <li>{t.n_coverage}</li>
      <li>{t.n_measures}</li>
      <li>{t.n_validate}</li>
      <li>{t.n_save}</li>
    </ol>
    <div class="row">
      <button class="primary" onclick={() => app.save()} data-testid="setup-save">{t.save_now}</button>
      <button onclick={() => (app.view = { kind: 'objects', collection: 'threats', selected: null })}>{t.go_threats}</button>
      <button onclick={() => (app.view = { kind: 'coverage' })}>{t.go_coverage}</button>
      <button onclick={() => (app.view = { kind: 'diagram' })}>{t.go_diagram}</button>
    </div>
  {/if}

  {#if step > 0}
    <nav class="pager" aria-label={t.title}>
      <button onclick={() => go(step - 1)} disabled={busy}>{t.back}</button>
      <span class="muted">{t.step} {step} {t.of} {STEPS.length}</span>
      {#if step < STEPS.length}
        <button class="primary" onclick={() => go(step + 1)} disabled={busy} data-testid="setup-next">{t.next}</button>
      {/if}
      <span class="grow"></span>
      <button class="link" onclick={() => (app.view = { kind: 'overview' })}>{t.skip}</button>
    </nav>
  {/if}
</section>

<style>
  .setup {
    max-width: 60rem;
    display: grid;
    gap: 0.5rem;
  }
  h1 {
    font-size: 1.3rem;
    margin: 0;
  }
  h2 {
    font-size: 1.15rem;
    margin: 0.5rem 0 0;
  }
  h3 {
    font-size: 1rem;
    margin: 0.75rem 0 0.25rem;
  }
  h4 {
    font-size: 0.9rem;
    margin: 0.6rem 0 0.2rem;
    color: var(--muted);
  }
  p {
    margin: 0.2rem 0;
  }
  .steps {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 0.75rem;
    list-style: none;
    padding: 0;
    margin: 0;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.5rem;
  }
  .steps li[aria-current='step'] button {
    font-weight: 700;
    text-decoration: underline;
  }
  .link {
    border: none;
    background: none;
    padding: 0;
    color: var(--accent);
    justify-self: start;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.6rem 0.9rem;
    display: grid;
    gap: 0.35rem;
  }
  .card button {
    justify-self: start;
  }
  .hint summary {
    cursor: pointer;
    color: var(--accent);
  }
  .row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }
  .row input,
  .row select {
    width: auto;
    flex: 1;
    min-width: 0;
  }
  .row input.short {
    flex: 0 0 7rem;
  }
  .item {
    border-bottom: 1px solid var(--border);
    padding: 0.25rem 0;
  }
  .item select {
    flex: 0 0 12rem;
  }
  .grow {
    flex: 1;
    min-width: 0;
  }
  .indicators {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
  }
  .split {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
    gap: 1rem;
  }
  .scroll {
    max-height: 26rem;
    overflow: auto;
    margin-top: 0.4rem;
  }
  .plain {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .pick {
    width: 100%;
    text-align: left;
    margin-bottom: 0.2rem;
  }
  .pick.active {
    border-color: var(--accent);
    outline: 1px solid var(--accent);
  }
  .preview {
    height: 26rem;
  }
  .preview :global(.canvas) {
    min-height: 0;
  }
  .grid4 {
    grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
    align-items: end;
  }
  .grid3 {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
    align-items: start;
    margin-top: 0.75rem;
  }
  .grid3 button {
    margin-top: 1.4rem;
  }
  .suggestion label {
    display: flex;
    gap: 0.5rem;
    align-items: start;
    padding: 0.3rem 0;
    border-top: 1px solid var(--border);
  }
  .suggestion input {
    width: auto;
    margin-top: 0.2rem;
  }
  .block {
    display: block;
  }
  .small {
    font-size: 0.9em;
  }
  .tag {
    margin-left: 0.5rem;
    color: var(--warning);
    font-size: 0.9em;
  }
  .checks li {
    padding: 0.1rem 0;
  }
  .pager {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    margin-top: 1rem;
    border-top: 1px solid var(--border);
    padding-top: 0.75rem;
  }
  @media (max-width: 900px) {
    .split,
    .indicators,
    .grid4,
    .grid3 {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
