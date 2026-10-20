<script lang="ts">
  import { api, ApiError } from '../api'
  import { PRODUCT_NAME } from '../branding'
  import { tr } from '../i18n'
  import { app, type View } from '../state.svelte'
  import type { ProjectInfo } from '../types'

  let openPath = $state('')
  let newPath = $state('')
  let newName = $state('')
  let template = $state<'tr' | 'empty'>('tr')
  let error = $state('')
  const lang = $derived(app.lang)

  async function run(fn: () => Promise<ProjectInfo>, view?: View) {
    error = ''
    try {
      await app.loadProject(await fn())
      app.view = view ?? app.home()
    } catch (e) {
      app.view = { kind: 'start' }
      error = e instanceof ApiError ? e.message : String(e)
    }
  }

  // Native folder dialog, shown by the local server process; null when cancelled.
  async function browse(initial: string): Promise<string | null> {
    error = ''
    try {
      const r = await api<{ path: string | null }>('POST', '/pick-folder', {
        title: tr(lang, 'pick_folder'),
        initial,
      })
      return r.path
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e)
      return null
    }
  }

  const open = (path: string) => run(() => api<ProjectInfo>('POST', '/project/open', { path }))
  const create = () =>
    run(() =>
      api<ProjectInfo>('POST', '/project/new', {
        path: newPath,
        name: newName,
        template,
        language: app.lang,
      }),
      // new projects start in the setup wizard
      { kind: 'setup', step: 0 },
    )
</script>

<section class="start">
  <h1>{PRODUCT_NAME} <span class="muted">{app.version}</span></h1>
  {#if error}<p class="error" role="alert">{error}</p>{/if}

  {#if app.recent.length}
    <h2>{tr(lang, 'recent')}</h2>
    <ul>
      {#each app.recent as path}
        <li><button class="rowlink" onclick={() => open(path)}>{path}</button></li>
      {/each}
    </ul>
  {/if}

  <form onsubmit={(e) => { e.preventDefault(); open(openPath) }}>
    <h2>{tr(lang, 'open_project')}</h2>
    <label for="open-path">{tr(lang, 'path')}</label>
    <div class="row">
      <input id="open-path" bind:value={openPath} required data-testid="open-path" />
      <button
        type="button"
        data-testid="browse-open"
        onclick={async () => {
          const path = await browse(openPath)
          if (path) {
            openPath = path
            open(path)
          }
        }}>{tr(lang, 'browse')}</button
      >
      <button class="primary" type="submit">{tr(lang, 'open')}</button>
    </div>
  </form>

  <form onsubmit={(e) => { e.preventDefault(); create() }}>
    <h2>{tr(lang, 'new_project')}</h2>
    <label for="new-path">{tr(lang, 'path')}</label>
    <div class="row">
      <input id="new-path" bind:value={newPath} required data-testid="new-path" />
      <button
        type="button"
        data-testid="browse-new"
        onclick={async () => {
          newPath = (await browse(newPath)) ?? newPath
        }}>{tr(lang, 'browse')}</button
      >
    </div>
    <label for="new-name">{tr(lang, 'name')}</label>
    <input id="new-name" bind:value={newName} data-testid="new-name" />
    <label for="new-template">{tr(lang, 'template')}</label>
    <select id="new-template" bind:value={template}>
      <option value="tr">{tr(lang, 'template_tr')}</option>
      <option value="empty">{tr(lang, 'template_empty')}</option>
    </select>
    <button class="primary" type="submit" data-testid="create-project">{tr(lang, 'create')}</button>
  </form>
</section>

<style>
  .start {
    max-width: 40rem;
    display: grid;
    gap: 0.5rem;
  }
  form {
    display: grid;
    gap: 0.35rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.75rem 1rem 1rem;
  }
  form button {
    justify-self: start;
    margin-top: 0.4rem;
  }
  .row {
    display: flex;
    gap: 0.5rem;
  }
  .row button {
    margin: 0;
  }
  .row input {
    flex: 1;
    min-width: 0;
  }
  h2 {
    font-size: 1.05rem;
    margin: 0.25rem 0;
  }
  ul {
    padding-left: 1.2rem;
  }
  .rowlink {
    border: none;
    background: none;
    padding: 0;
    color: var(--accent);
    text-align: left;
  }
</style>
