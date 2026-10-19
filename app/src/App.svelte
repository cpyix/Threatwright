<script lang="ts">
  import { onMount } from 'svelte'
  import { PRODUCT_NAME } from './branding'
  import { tr, type Key } from './i18n'
  import Assistant from './lib/Assistant.svelte'
  import Coverage from './lib/Coverage.svelte'
  import CyberCauseDialog from './lib/CyberCauseDialog.svelte'
  import Diagram from './lib/diagram/Diagram.svelte'
  import Objects from './lib/Objects.svelte'
  import Overview from './lib/Overview.svelte'
  import Settings from './lib/Settings.svelte'
  import Start from './lib/Start.svelte'
  import Validation from './lib/Validation.svelte'
  import { app } from './state.svelte'
  import { COLLECTIONS } from './types'

  const lang = $derived(app.lang)
  const errors = $derived(app.issues.filter((i) => i.severity === 'error').length)

  onMount(() => {
    app.init()
    const poll = setInterval(() => app.pollChanges().catch(() => {}), 3000)
    return () => clearInterval(poll)
  })

  function onkeydown(e: KeyboardEvent) {
    const mod = e.ctrlKey || e.metaKey
    if (mod && e.key.toLowerCase() === 's') {
      e.preventDefault()
      app.save()
      return
    }
    const editing = e.target instanceof HTMLElement && e.target.closest('input, textarea, select')
    if (!mod || editing) return
    if (e.key.toLowerCase() === 'z' && !e.shiftKey && app.project?.can_undo) {
      e.preventDefault()
      app.undoRedo('undo')
    } else if ((e.key.toLowerCase() === 'y' || (e.key.toLowerCase() === 'z' && e.shiftKey)) && app.project?.can_redo) {
      e.preventDefault()
      app.undoRedo('redo')
    }
  }

  function onbeforeunload(e: BeforeUnloadEvent) {
    if (app.project?.dirty) {
      e.preventDefault()
    }
  }

  async function switchModel(name: string) {
    app.modelName = name
    await app.refreshModel()
  }
</script>

<svelte:window {onkeydown} {onbeforeunload} />
<svelte:head>
  <title>{app.project ? `${app.project.config.name} – ${PRODUCT_NAME}` : PRODUCT_NAME}</title>
</svelte:head>

<header class="top">
  <strong class="brand">{PRODUCT_NAME}</strong>
  {#if app.project}
    <span class="project">{app.project.config.name}</span>
    {#if Object.keys(app.project.models).length > 1}
      <label class="sr-only" for="model-select">{tr(lang, 'model')}</label>
      <select id="model-select" value={app.modelName} onchange={(e) => switchModel(e.currentTarget.value)}>
        {#each Object.entries(app.project.models) as [name, m]}<option value={name}>{m.title}</option>{/each}
      </select>
    {/if}
    <span class="spacer"></span>
    <button onclick={() => app.undoRedo('undo')} disabled={!app.project.can_undo} title="Ctrl+Z">{tr(lang, 'undo')}</button>
    <button onclick={() => app.undoRedo('redo')} disabled={!app.project.can_redo} title="Ctrl+Y">{tr(lang, 'redo')}</button>
    <button class="primary" onclick={() => app.save()} title="Ctrl+S" data-testid="save">
      {tr(lang, 'save')}{app.project.dirty ? ' •' : ''}
    </button>
  {:else}
    <span class="spacer"></span>
  {/if}
  <button onclick={() => (app.lang = lang === 'de' ? 'en' : 'de')} aria-label="Sprache / language">
    {lang === 'de' ? 'EN' : 'DE'}
  </button>
</header>

{#if app.externalChange}
  <div class="banner" role="alert">
    {tr(lang, 'external_changed')}
    <button onclick={() => app.reload()}>{tr(lang, 'reload_discard')}</button>
    <button onclick={() => (app.externalChange = false)}>{tr(lang, 'ignore')}</button>
  </div>
{/if}

<div class="layout">
  <nav aria-label="Navigation">
    <button class:active={app.view.kind === 'start'} onclick={() => (app.view = { kind: 'start' })}>{tr(lang, 'start')}</button>
    {#if app.project}
      <button class:active={app.view.kind === 'overview'} onclick={() => (app.view = { kind: 'overview' })}>{tr(lang, 'overview')}</button>
      <button class:active={app.view.kind === 'diagram'} onclick={() => (app.view = { kind: 'diagram' })} data-testid="nav-diagram">{tr(lang, 'diagram')}</button>
      <button class:active={app.view.kind === 'assistant'} onclick={() => (app.view = { kind: 'assistant', target: null })} data-testid="nav-assistant">{tr(lang, 'assistant')}</button>
      <button class:active={app.view.kind === 'coverage'} onclick={() => (app.view = { kind: 'coverage' })} data-testid="nav-coverage">{tr(lang, 'coverage')}</button>
      {#each COLLECTIONS as c}
        <button
          class:active={app.view.kind === 'objects' && app.view.collection === c}
          onclick={() => (app.view = { kind: 'objects', collection: c, selected: null })}
          data-testid="nav-{c}">{tr(lang, c as Key)}</button
        >
      {/each}
      <button class:active={app.view.kind === 'validation'} onclick={() => (app.view = { kind: 'validation' })} data-testid="nav-validation">
        {tr(lang, 'validation')} {#if errors}<span class="count error">{errors}</span>{/if}
      </button>
      <button class:active={app.view.kind === 'settings'} onclick={() => (app.view = { kind: 'settings' })} data-testid="nav-settings">{tr(lang, 'settings')}</button>
    {/if}
  </nav>

  <main>
    {#if app.view.kind === 'start' || !app.project}
      <Start />
    {:else if !app.model}
      <p class="muted">{tr(lang, 'project_none')}</p>
    {:else if app.view.kind === 'overview'}
      <Overview />
    {:else if app.view.kind === 'validation'}
      <Validation />
    {:else if app.view.kind === 'diagram'}
      <Diagram />
    {:else if app.view.kind === 'assistant'}
      <Assistant target={app.view.target} />
    {:else if app.view.kind === 'coverage'}
      <Coverage />
    {:else if app.view.kind === 'settings'}
      <Settings />
    {:else if app.view.kind === 'objects'}
      <Objects collection={app.view.collection} selected={app.view.selected} />
    {/if}
  </main>
</div>

<CyberCauseDialog />

<div class="toast" role="status" aria-live="polite" data-testid="toast">
  {#if app.message}{tr(lang, app.message as Key)}{/if}
</div>

<style>
  .top {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.5rem 1rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .top select {
    width: auto;
  }
  .brand {
    font-size: 1.05rem;
  }
  .project {
    color: var(--muted);
  }
  .spacer {
    flex: 1;
  }
  .banner {
    padding: 0.5rem 1rem;
    background: var(--risk-3);
    color: var(--risk-text);
    display: flex;
    gap: 0.75rem;
    align-items: center;
  }
  .layout {
    display: grid;
    grid-template-columns: 12rem 1fr;
    min-height: calc(100vh - 3rem);
  }
  nav {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    padding: 0.75rem 0.5rem;
    border-right: 1px solid var(--border);
  }
  nav button {
    text-align: left;
    border: none;
    background: none;
    padding: 0.4rem 0.6rem;
  }
  nav button.active {
    background: var(--surface-2);
    font-weight: 600;
  }
  .count {
    font-weight: 700;
  }
  main {
    padding: 1rem 1.25rem;
    min-width: 0;
  }
  .toast {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
  }
  .toast:not(:empty) {
    background: var(--text);
    color: var(--bg);
    padding: 0.5rem 0.9rem;
    border-radius: var(--radius);
  }
</style>
