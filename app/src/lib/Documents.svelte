<script lang="ts">
  import { api, ApiError, download } from '../api'
  import { tr } from '../i18n'
  import { app } from '../state.svelte'
  import type { I18n } from '../types'

  type Template = {
    id: string
    name: I18n
    description: I18n | null
    formats: string[]
    scope: 'model' | 'project'
    origin: string
    active: boolean
  }

  let templates = $state<Template[]>([])
  let selected = $state<string | null>(null)
  let previewUrl = $state<string | null>(null)
  let written = $state<string[]>([])
  let busy = $state(false)
  let error = $state('')
  const lang = $derived(app.lang)
  const current = $derived(templates.find((t) => t.id === selected) ?? null)

  $effect(() => {
    void app.project?.root
    api<Template[]>('GET', '/templates')
      .then((t) => {
        templates = t
        selected ??= t.find((x) => x.active)?.id ?? t[0]?.id ?? null
      })
      .catch((e) => (error = e instanceof ApiError ? e.message : String(e)))
  })

  async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
    error = ''
    busy = true
    try {
      return await fn()
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e)
    } finally {
      busy = false
    }
  }

  const preview = () =>
    run(async () => {
      const r = await api<{ url: string }>('POST', '/preview', { template: selected, model: app.modelName })
      previewUrl = r.url
    })

  const build = (format: string) =>
    run(async () => {
      const r = await api<{ written: string[] }>('POST', '/build', {
        template: selected,
        model: current?.scope === 'model' ? app.modelName : '',
        format,
      })
      written = r.written
      // on a server the build folder is not on this machine: hand the files to the browser
      if (app.server) for (const p of r.written) await download(`/build/${encodeURIComponent(p.split('/').pop()!)}`, p.split('/').pop()!)
    })
</script>

<section class="documents">
  <h1>{tr(lang, 'documents')}</h1>
  {#if app.project?.dirty}
    <p class="warning" role="alert">{tr(lang, 'save_before_build')}</p>
  {/if}
  <div class="layout">
    <div class="list" role="listbox" aria-label={tr(lang, 'template')}>
      {#each templates as t (t.id)}
        <button
          role="option"
          aria-selected={t.id === selected}
          class:selected={t.id === selected}
          onclick={() => {
            selected = t.id
            previewUrl = null
          }}
          data-testid="template-{t.id}"
        >
          <strong>{t.name[lang]}</strong>
          <span class="muted">{t.formats.join(' · ')} · {t.origin}</span>
        </button>
      {/each}
    </div>

    <div class="detail">
      {#if current}
        {#if current.description}<p>{current.description[lang]}</p>{/if}
        <div class="row">
          <button onclick={preview} disabled={busy} data-testid="preview">{tr(lang, 'preview')}</button>
          {#each current.formats as f}
            <button class="primary" onclick={() => build(f)} disabled={busy || app.project?.dirty} data-testid="build-{f}">
              {f.toUpperCase()}
            </button>
          {/each}
          {#if !app.server}
            <button onclick={() => run(() => api('POST', '/open-build-folder'))}>{tr(lang, 'open_folder')}</button>
          {/if}
        </div>
        {#if error}<pre class="error" role="alert">{error}</pre>{/if}
        {#if written.length}
          <p class="ok" data-testid="written">{tr(lang, 'written')}: {written.join(', ')}</p>
        {/if}
        {#if previewUrl}
          <iframe title={tr(lang, 'preview')} src={previewUrl} sandbox="" data-testid="preview-frame"></iframe>
        {/if}
      {/if}
    </div>
  </div>
</section>

<style>
  h1 {
    font-size: 1.3rem;
    margin-top: 0;
  }
  .layout {
    display: grid;
    grid-template-columns: 18rem minmax(0, 1fr);
    gap: 1rem;
  }
  .list {
    display: grid;
    gap: 0.4rem;
    align-content: start;
  }
  .list button {
    display: grid;
    text-align: left;
    gap: 0.15rem;
  }
  .list button.selected {
    border-color: var(--accent);
    outline: 1px solid var(--accent);
  }
  .row {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  iframe {
    width: 100%;
    height: calc(100vh - 16rem);
    margin-top: 0.75rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: #fff;
  }
  pre.error {
    white-space: pre-wrap;
  }
</style>
