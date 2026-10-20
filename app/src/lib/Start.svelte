<script lang="ts">
  import { api, ApiError, download, upload } from '../api'
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

  // --- server mode: projects in the workspace, upload from the user's machine --------
  let serverProjects = $state<{ path: string; name: string }[]>([])
  let panel = $state<'new' | 'upload' | null>(null) // server mode: which form is unfolded
  const isOpen = (path: string) =>
    !!app.project && app.project.root.replace(/\\/g, '/').replace(/\/$/, '').endsWith(`/${path}`)
  let zip = $state<File | null>(null)
  let zipFolder = $state('')

  $effect(() => {
    if (!app.server) return
    void app.project // refresh after opening, creating or uploading
    api<{ projects: { path: string; name: string }[] }>('GET', '/workspace')
      .then((r) => (serverProjects = r.projects))
      .catch(() => (serverProjects = []))
  })

  const importZip = () => {
    const file = zip!
    const folder = zipFolder.trim() || file.name.replace(/\.zip$/i, '')
    return run(() => upload<ProjectInfo>(`/project/upload?folder=${encodeURIComponent(folder)}`, file))
  }

  async function downloadZip() {
    error = ''
    try {
      await download('/project/download', `${app.project?.config.name ?? 'project'}.zip`)
    } catch (e) {
      error = e instanceof ApiError ? e.message : String(e)
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

  {#if app.project}
    <div class="card">
      <h2>{tr(lang, 'current_project')}: {app.project.config.name}</h2>
      <p class="muted">{tr(lang, 'download_help')}</p>
      <button onclick={downloadZip} data-testid="download-project">{tr(lang, 'download_zip')}</button>
    </div>
  {/if}

  {#if app.server}
    <div class="overview-head">
      <h2>{tr(lang, 'server_projects')}</h2>
      <button class="primary" onclick={() => (panel = panel === 'new' ? null : 'new')} aria-expanded={panel === 'new'} data-testid="show-new-project">
        + {tr(lang, 'new_project')}
      </button>
      <button onclick={() => (panel = panel === 'upload' ? null : 'upload')} aria-expanded={panel === 'upload'} data-testid="show-upload">
        {tr(lang, 'upload_project_short')}
      </button>
    </div>
    <ul class="projects" data-testid="server-projects">
      {#each serverProjects as p (p.path)}
        {@const current = isOpen(p.path)}
        <li>
          <button
            class="project"
            class:current
            onclick={() => (current ? (app.view = app.home()) : open(p.path))}
            data-testid="open-server-{p.path}"
          >
            <strong>{p.name}</strong>
            <span class="muted">{p.path}</span>
            {#if current}<span class="badge">{tr(lang, 'is_open')}</span>{/if}
          </button>
        </li>
      {:else}
        <li class="muted">{tr(lang, 'no_server_projects')}</li>
      {/each}
    </ul>

    {#if panel === 'upload'}
    <form onsubmit={(e) => { e.preventDefault(); importZip() }}>
      <h2>{tr(lang, 'upload_project')}</h2>
      <p class="muted">{tr(lang, 'upload_help')}</p>
      <label for="zip-file">{tr(lang, 'zip_file')}</label>
      <input
        id="zip-file"
        type="file"
        accept=".zip,application/zip"
        required
        onchange={(e) => (zip = e.currentTarget.files?.[0] ?? null)}
        data-testid="zip-file"
      />
      <label for="zip-folder">{tr(lang, 'folder_name')}</label>
      <input id="zip-folder" bind:value={zipFolder} placeholder={zip?.name.replace(/\.zip$/i, '') ?? ''} />
      <button class="primary" type="submit" disabled={!zip} data-testid="upload-project">{tr(lang, 'upload')}</button>
    </form>
    {/if}
  {:else}
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
  {/if}

  {#if !app.server || panel === 'new'}
  <form onsubmit={(e) => { e.preventDefault(); create() }}>
    <h2>{tr(lang, 'new_project')}</h2>
    <!-- on a server: just a folder name inside the workspace; locally: any folder -->
    <label for="new-path">{tr(lang, app.server ? 'folder_name' : 'path')}</label>
    <div class="row">
      <input id="new-path" bind:value={newPath} required data-testid="new-path" />
      {#if !app.server}
        <button
          type="button"
          data-testid="browse-new"
          onclick={async () => {
            newPath = (await browse(newPath)) ?? newPath
          }}>{tr(lang, 'browse')}</button
        >
      {/if}
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
  {/if}
</section>

<style>
  .start {
    max-width: 40rem;
    display: grid;
    gap: 0.5rem;
  }
  .overview-head {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
  }
  .overview-head h2 {
    margin-right: auto;
  }
  .projects {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 0.6rem;
  }
  .project {
    width: 100%;
    min-height: 5.5rem;
    display: grid;
    align-content: start;
    gap: 0.25rem;
    text-align: left;
    padding: 0.75rem 0.9rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    cursor: pointer;
  }
  .project:hover {
    border-color: var(--accent);
  }
  .project.current {
    border-color: var(--accent);
    box-shadow: inset 3px 0 0 var(--accent);
  }
  .project span {
    font-size: 0.85em;
    overflow-wrap: anywhere;
  }
  .badge {
    justify-self: start;
    color: var(--accent);
    font-weight: 600;
  }
  .card {
    display: grid;
    gap: 0.35rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.75rem 1rem 1rem;
  }
  .card > button {
    justify-self: start;
  }
  .card p {
    margin: 0;
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
