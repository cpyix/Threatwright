<script lang="ts">
  import { api, ApiError } from '../api'
  import { tr } from '../i18n'
  import { app } from '../state.svelte'
  import Catalogs from './Catalogs.svelte'

  let kind = $state<'gitlab' | 'github'>('gitlab')
  let image = $state('')
  let ci = $state<{ text: string; target: string; exists: boolean } | null>(null)
  let note = $state('')
  const lang = $derived(app.lang)

  // lifecycle, support period (CRA Art. 13(8)) and next review of the threat model
  let product = $state({ lifecycle: 'development', support_until: '', next_review: '' })
  let productNote = $state('')
  $effect(() => {
    const c = app.project?.config
    if (c) product = { lifecycle: c.lifecycle, support_until: c.support_until ?? '', next_review: c.next_review ?? '' }
  })

  async function saveProduct() {
    productNote = ''
    try {
      app.project = await api('PUT', '/project/settings', {
        lifecycle: product.lifecycle,
        support_until: product.support_until || null,
        next_review: product.next_review || null,
      })
      await app.afterChange()
      productNote = tr(lang, 'settings_applied')
    } catch (e) {
      productNote = e instanceof ApiError ? e.message : String(e)
    }
  }

  async function load() {
    note = ''
    const q = image ? `?image=${encodeURIComponent(image)}` : ''
    try {
      ci = await api('GET', `/ci/${kind}${q}`)
    } catch (e) {
      note = e instanceof ApiError ? e.message : String(e)
    }
  }

  $effect(() => {
    void kind
    load()
  })

  async function copy() {
    if (!ci) return
    await navigator.clipboard.writeText(ci.text)
    note = tr(lang, 'copied')
  }

  async function write() {
    if (!ci) return
    if (ci.exists && !confirm(`${ci.target}: ${tr(lang, 'overwrite_q')}`)) return
    const r = await api<{ written: string }>('POST', `/ci/${kind}/write`, { image: image || null, overwrite: ci.exists })
    note = `${tr(lang, 'written')}: ${r.written}`
    await load()
  }
</script>

<section class="settings">
  <h1>{tr(lang, 'settings')}</h1>

  <h2>{tr(lang, 'product_lifecycle')}</h2>
  <p class="muted">{tr(lang, 'product_lifecycle_help')}</p>
  <form class="grid" onsubmit={(e) => { e.preventDefault(); saveProduct() }}>
    <label for="s-lifecycle">{tr(lang, 'lifecycle')}</label>
    <select id="s-lifecycle" bind:value={product.lifecycle} data-testid="settings-lifecycle">
      <option value="development">{tr(lang, 'lifecycle_development')}</option>
      <option value="post_market">{tr(lang, 'lifecycle_post_market')}</option>
    </select>
    <label for="s-support">{tr(lang, 'support_until')}</label>
    <input id="s-support" type="date" bind:value={product.support_until} data-testid="settings-support-until" />
    <label for="s-review">{tr(lang, 'next_review')}</label>
    <input id="s-review" type="date" bind:value={product.next_review} data-testid="settings-next-review" />
    <span></span>
    <button type="submit" class="primary" data-testid="settings-apply">{tr(lang, 'apply')}</button>
  </form>
  {#if productNote}<p role="status">{productNote}</p>{/if}

  <h2>{tr(lang, 'method')}</h2>
  <p>
    {app.method?.title[lang] ?? app.project?.config.method}<br />
    <span class="muted">
      {tr(lang, app.method?.risk_matrix.matrix_row_from_exposure === 'literal' ? 'matrix_literal' : 'matrix_inverted')}
      {tr(lang, 'overrides_hint')}
    </span>
  </p>
  <p>{tr(lang, 'libraries')}: {app.project?.config.libraries.join(', ') || '–'}</p>

  <Catalogs />

  <h2>{tr(lang, 'ci_pipeline')}</h2>
  <p class="muted">{tr(lang, 'ci_help')}</p>
  <div class="row">
    <label>
      <input type="radio" bind:group={kind} value="gitlab" /> GitLab
    </label>
    <label>
      <input type="radio" bind:group={kind} value="github" /> GitHub Actions
    </label>
    <input placeholder={tr(lang, 'ci_image')} bind:value={image} onchange={load} aria-label={tr(lang, 'ci_image')} />
  </div>
  {#if ci}
    <!-- svelte-ignore a11y_no_noninteractive_tabindex (scrollable region must be keyboard reachable) -->
    <pre class="ci" data-testid="ci-text" tabindex="0" aria-label={tr(lang, 'ci_pipeline')}>{ci.text}</pre>
    <div class="row">
      <button class="primary" onclick={copy}>{tr(lang, 'copy')}</button>
      <button onclick={write}>{tr(lang, 'write_to')} {ci.target}</button>
    </div>
  {/if}
  {#if note}<p role="status">{note}</p>{/if}
</section>

<style>
  .settings {
    max-width: 60rem;
  }
  h1 {
    font-size: 1.3rem;
    margin-top: 0;
  }
  h2 {
    font-size: 1.05rem;
    margin-top: 1.5rem;
  }
  .grid {
    display: grid;
    grid-template-columns: max-content minmax(0, 16rem);
    gap: 0.5rem 0.75rem;
    align-items: center;
  }
  .grid button {
    justify-self: start;
  }
  .row {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
    margin: 0.5rem 0;
  }
  .row label {
    display: flex;
    gap: 0.3rem;
    align-items: center;
  }
  .row input[type='radio'] {
    width: auto;
  }
  .row input:not([type]) {
    max-width: 26rem;
  }
  pre.ci {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.75rem;
    max-height: 26rem;
    overflow: auto;
    font-size: 12px;
  }
</style>
