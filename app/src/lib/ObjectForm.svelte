<script lang="ts">
  import { api, ApiError } from '../api'
  import { clean, FIELDS, getPath, setPath, type Field } from '../fields'
  import { label, tr } from '../i18n'
  import { app } from '../state.svelte'
  import type { Collection, ModelPayload, Obj, ThreatEvaluation } from '../types'
  import Assessment from './Assessment.svelte'
  import CustomFieldInput from './CustomField.svelte'
  import MultiSelect from './MultiSelect.svelte'

  let {
    collection,
    source,
    onsaved,
    onclose,
  }: {
    collection: Collection
    source: Partial<Obj>
    onsaved: (id: string, created: boolean) => void
    onclose: () => void
  } = $props()

  // svelte-ignore state_referenced_locally (form keeps its own draft of the object)
  let draft = $state<Record<string, any>>(structuredClone($state.snapshot(source)))
  let error = $state('')
  let live = $state<ThreatEvaluation | null>(null)
  let renaming = $state<string | null>(null)
  const lang = $derived(app.lang)
  const isNew = $derived(!draft.id)
  const custom = $derived(app.project?.custom_fields.fields[collection.replace(/s$/, '')] ?? [])

  function set(path: string, value: any) {
    setPath(draft, path, value)
    if (collection === 'threats' && path === 'targets') prefillFromZone()
  }

  /** Fill empty environment fields from the zone of the first targeted element. */
  function prefillFromZone() {
    const target = app.objects('elements').find((e) => draft.targets?.includes(e.id))
    const zone = app.model?.meta.zones.find((z) => z.id === target?.zone)
    for (const [k, v] of Object.entries(zone?.environment ?? {})) {
      if (v && !draft.assessment?.[k]) setPath(draft, `assessment.${k}`, v)
    }
  }

  // Live risk while editing a threat (computed by the core on the server).
  let timer: ReturnType<typeof setTimeout> | undefined
  $effect(() => {
    if (collection !== 'threats') return
    const body = clean($state.snapshot(draft))
    clearTimeout(timer)
    timer = setTimeout(async () => {
      try {
        live = await api<ThreatEvaluation>('POST', `/models/${app.modelName}/evaluate`, body)
      } catch {
        live = null
      }
    }, 150)
  })

  async function apply() {
    error = ''
    const body = clean($state.snapshot(draft))
    try {
      const path = `/models/${app.modelName}/${collection}`
      const r = await api<{ object: Obj; model: ModelPayload }>(
        isNew ? 'POST' : 'PUT',
        isNew ? path : `${path}/${draft.id}`,
        body,
      )
      const created = isNew
      draft = structuredClone(r.object)
      await app.afterChange(r.model)
      onsaved(r.object.id, created)
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e)
    }
  }

  async function remove() {
    const model = await api<ModelPayload>('DELETE', `/models/${app.modelName}/${collection}/${draft.id}`)
    await app.afterChange(model)
    onclose()
  }

  async function rename() {
    error = ''
    try {
      const r = await api<{ id: string; model: ModelPayload }>(
        'POST',
        `/models/${app.modelName}/${collection}/${draft.id}/rename`,
        { id: renaming },
      )
      renaming = null
      await app.afterChange(r.model)
      onsaved(r.id, false)
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e)
    }
  }

  function fieldLabel(f: Field): string {
    const dim = f.key.match(/^amplifier\.([cia])$/)
    return tr(lang, f.label) + (dim ? ` ${dim[1].toUpperCase()}` : '')
  }

  const fid = (key: string) => `f-${key.replace(/\./g, '-')}`
</script>

<form
  class="form"
  onsubmit={(e) => {
    e.preventDefault()
    apply()
  }}
  data-testid="object-form"
>
  <header>
    {#if renaming !== null}
      <span class="rename">
        <input bind:value={renaming} aria-label={tr(lang, 'rename_id')} />
        <button type="button" onclick={rename}>{tr(lang, 'apply')}</button>
        <button type="button" onclick={() => (renaming = null)}>{tr(lang, 'cancel')}</button>
      </span>
    {:else}
      <h2>
        {isNew ? tr(lang, 'new') : draft.id}
        {#if !isNew}<button type="button" class="link" onclick={() => (renaming = draft.id)} title={tr(lang, 'rename_id')}>✎</button>{/if}
      </h2>
    {/if}
    <div class="actions">
      <button type="submit" class="primary" data-testid="apply">{isNew ? tr(lang, 'create') : tr(lang, 'apply')}</button>
      {#if !isNew}<button type="button" onclick={remove}>{tr(lang, 'delete')}</button>{/if}
      <button type="button" onclick={onclose}>{tr(lang, 'cancel')}</button>
    </div>
  </header>
  {#if error}<pre class="error" role="alert">{error}</pre>{/if}

  {#each FIELDS[collection] as f (f.key)}
    {@const value = getPath(draft, f.key)}
    <div class="field">
      {#if f.type === 'bool'}
        <label class="check">
          <input id={fid(f.key)} type="checkbox" checked={!!value} onchange={(e) => set(f.key, e.currentTarget.checked)} />
          {fieldLabel(f)}
        </label>
      {:else}
        <label id="{fid(f.key)}-label" for={fid(f.key)}>{fieldLabel(f)}{f.required ? ' *' : ''}</label>
        {#if f.type === 'text' || f.type === 'date'}
          <input id={fid(f.key)} type={f.type === 'date' ? 'date' : 'text'} value={value ?? ''} oninput={(e) => set(f.key, e.currentTarget.value)} data-testid="field-{f.key}" />
        {:else if f.type === 'number'}
          <input id={fid(f.key)} type="number" step="0.1" min="0" value={value ?? ''} oninput={(e) => set(f.key, e.currentTarget.value === '' ? '' : Number(e.currentTarget.value))} />
        {:else if f.type === 'longtext'}
          <textarea id={fid(f.key)} value={value ?? ''} oninput={(e) => set(f.key, e.currentTarget.value)} data-testid="field-{f.key}"></textarea>
        {:else if f.type === 'select'}
          <select id={fid(f.key)} value={value ?? ''} onchange={(e) => set(f.key, e.currentTarget.value)} data-testid="field-{f.key}">
            <option value="">–</option>
            {#each f.options?.() ?? [] as o}<option value={o.value}>{label(lang, o.label)}</option>{/each}
          </select>
        {:else if f.type === 'tristate'}
          <select id={fid(f.key)} value={value === true ? 'yes' : value === false ? 'no' : ''} onchange={(e) => set(f.key, e.currentTarget.value === '' ? '' : e.currentTarget.value === 'yes')} data-testid="field-{f.key}">
            <option value="">{tr(lang, 'unanswered')}</option>
            <option value="yes">{tr(lang, 'yes')}</option>
            <option value="no">{tr(lang, 'no')}</option>
          </select>
        {:else if f.type === 'multi'}
          <MultiSelect id={fid(f.key)} options={f.options?.() ?? []} value={value ?? []} onchange={(v) => set(f.key, v)} />
        {/if}
      {/if}
    </div>
    {#if collection === 'threats' && f.key === 'consequence'}
      <Assessment prefix="assessment" value={draft.assessment} evaluation={live?.assessment} suggestion={live?.suggestion} {set} />
      <Assessment prefix="residual" value={draft.residual} evaluation={live?.residual} {set} />
    {/if}
  {/each}

  {#if custom.length}
    <fieldset>
      <legend>{tr(lang, 'custom')}</legend>
      {#each custom as c (c.name)}
        <div class="field">
          <label for="custom-{c.name}">{c.label?.[lang] ?? c.name}{c.required ? ' *' : ''}</label>
          <CustomFieldInput field={c} value={draft.custom?.[c.name]} set={(v) => set(`custom.${c.name}`, v)} />
          {#if c.help?.[lang]}<small class="muted">{c.help[lang]}</small>{/if}
        </div>
      {/each}
    </fieldset>
  {/if}
</form>

<style>
  .form {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 0.7rem;
  }
  header {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    background: var(--bg);
    padding: 0.25rem 0;
    z-index: 1;
  }
  h2 {
    margin: 0;
    font-size: 1.15rem;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .field {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 0.2rem;
  }
  .check {
    display: flex;
    gap: 0.4rem;
    align-items: center;
  }
  .check input {
    width: auto;
  }
  .rename {
    display: flex;
    gap: 0.3rem;
  }
  .rename input {
    width: 9rem;
  }
  .link {
    border: none;
    background: none;
    color: var(--accent);
    padding: 0 0.25rem;
  }
  pre.error {
    white-space: pre-wrap;
    margin: 0;
  }
  fieldset {
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }
</style>
