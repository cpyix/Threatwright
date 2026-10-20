<script lang="ts">
  import ArrowRightLeft from '@lucide/svelte/icons/arrow-right-left'
  import Box from '@lucide/svelte/icons/box'
  import CircleCheckBig from '@lucide/svelte/icons/circle-check-big'
  import FileText from '@lucide/svelte/icons/file-text'
  import FolderOpen from '@lucide/svelte/icons/folder-open'
  import Gem from '@lucide/svelte/icons/gem'
  import Grid3x3 from '@lucide/svelte/icons/grid-3x3'
  import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard'
  import ListChecks from '@lucide/svelte/icons/list-checks'
  import MessageCircleQuestion from '@lucide/svelte/icons/message-circle-question'
  import PanelLeftClose from '@lucide/svelte/icons/panel-left-close'
  import PanelLeftOpen from '@lucide/svelte/icons/panel-left-open'
  import Settings from '@lucide/svelte/icons/settings'
  import ShieldAlert from '@lucide/svelte/icons/shield-alert'
  import ShieldCheck from '@lucide/svelte/icons/shield-check'
  import ShieldQuestion from '@lucide/svelte/icons/shield-question'
  import Wand from '@lucide/svelte/icons/wand-sparkles'
  import Workflow from '@lucide/svelte/icons/workflow'
  import { onMount, type Component } from 'svelte'
  import { PRODUCT_NAME } from './branding'
  import { tr, type Key } from './i18n'
  import Assistant from './lib/Assistant.svelte'
  import Controls from './lib/Controls.svelte'
  import Coverage from './lib/Coverage.svelte'
  import CyberCauseDialog from './lib/CyberCauseDialog.svelte'
  import Diagram from './lib/diagram/Diagram.svelte'
  import Documents from './lib/Documents.svelte'
  import Objects from './lib/Objects.svelte'
  import Overview from './lib/Overview.svelte'
  import SettingsView from './lib/Settings.svelte'
  import Setup from './lib/Setup.svelte'
  import Start from './lib/Start.svelte'
  import Validation from './lib/Validation.svelte'
  import { app, type View } from './state.svelte'
  import type { Collection } from './types'

  const lang = $derived(app.lang)
  const errors = $derived(app.issues.filter((i) => i.severity === 'error').length)

  $effect(() => {
    document.documentElement.lang = lang // screen readers and hyphenation follow the UI language
  })

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

  type Item = { key: Key; icon: Component; view: () => View; active: (v: View) => boolean; testid?: string }
  const simple = (key: Key & View['kind'], icon: Component, view: () => View = () => ({ kind: key }) as View): Item => ({
    key,
    icon,
    view,
    active: (v) => v.kind === key,
  })
  const collection = (c: Collection, icon: Component): Item => ({
    key: c,
    icon,
    view: () => ({ kind: 'objects', collection: c, selected: null }),
    active: (v) => v.kind === 'objects' && v.collection === c,
  })
  // Four groups instead of 16 flat entries: build the model, analyse it, check and hand over, project.
  const groups = $derived<{ title: Key; items: Item[] }[]>(
    app.project
      ? [
          {
            title: 'nav_model',
            items: [
              simple('setup', Wand, () => ({ kind: 'setup', step: 0 })),
              simple('diagram', Workflow),
              simple('overview', LayoutDashboard),
              collection('elements', Box),
              collection('flows', ArrowRightLeft),
              collection('assets', Gem),
            ],
          },
          {
            title: 'nav_analyse',
            items: [
              simple('assistant', ShieldQuestion, () => ({ kind: 'assistant', target: null })),
              simple('coverage', Grid3x3),
              collection('threats', ShieldAlert),
              collection('measures', ShieldCheck),
              collection('questions', MessageCircleQuestion),
            ],
          },
          {
            title: 'nav_check',
            items: [simple('validation', CircleCheckBig), simple('documents', FileText), simple('controls', ListChecks)],
          },
          { title: 'nav_project', items: [simple('start', FolderOpen), simple('settings', Settings)] },
        ]
      : [{ title: 'nav_project', items: [simple('start', FolderOpen)] }],
  )

  // per-browser convenience only; storage may be unavailable
  let collapsed = $state(readCollapsed())
  function readCollapsed(): boolean {
    try {
      return localStorage.getItem('tw-nav-collapsed') === '1'
    } catch {
      return false
    }
  }
  function toggleNav() {
    collapsed = !collapsed
    try {
      localStorage.setItem('tw-nav-collapsed', collapsed ? '1' : '0')
    } catch {
      /* ignore */
    }
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
  <button onclick={() => app.setLang(lang === 'de' ? 'en' : 'de')} aria-label="Sprache / language">
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
  <nav aria-label="Navigation" class:collapsed>
    <button
      class="toggle"
      onclick={toggleNav}
      aria-expanded={!collapsed}
      title={tr(lang, collapsed ? 'nav_expand' : 'nav_collapse')}
      aria-label={tr(lang, collapsed ? 'nav_expand' : 'nav_collapse')}
    >
      {#if collapsed}<PanelLeftOpen size={18} aria-hidden="true" />{:else}<PanelLeftClose size={18} aria-hidden="true" />{/if}
    </button>
    {#each groups as g (g.title)}
      <div class="group" role="group" aria-label={tr(lang, g.title)}>
        <span class="group-title">{tr(lang, g.title)}</span>
        {#each g.items as item (item.key)}
          {@const Icon = item.icon}
          <button
            class:active={item.active(app.view)}
            onclick={() => (app.view = item.view())}
            title={collapsed ? tr(lang, item.key) : undefined}
            aria-current={item.active(app.view) ? 'page' : undefined}
            data-testid="nav-{item.testid ?? item.key}"
          >
            <Icon size={17} strokeWidth={1.75} aria-hidden="true" />
            <span class="label">{tr(lang, item.key)}</span>
            {#if item.key === 'validation' && errors}<span class="count error">{errors}</span>{/if}
          </button>
        {/each}
      </div>
    {/each}
  </nav>

  <main>
    {#if app.view.kind === 'start' || !app.project}
      <Start />
    {:else if app.view.kind === 'setup'}
      <Setup step={app.view.step} />
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
      <SettingsView />
    {:else if app.view.kind === 'controls'}
      <Controls />
    {:else if app.view.kind === 'documents'}
      <Documents />
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
    grid-template-columns: auto minmax(0, 1fr);
    min-height: calc(100vh - 3rem);
  }
  nav {
    width: 13rem;
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
    padding: 0.5rem 0.5rem 1rem;
    border-right: 1px solid var(--border);
  }
  nav.collapsed {
    width: 3.25rem;
  }
  .group {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }
  .group-title {
    padding: 0 0.6rem 0.15rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--muted);
  }
  nav button {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    text-align: left;
    border: none;
    background: none;
    padding: 0.4rem 0.6rem;
    border-radius: var(--radius);
  }
  nav button:hover {
    background: var(--surface-2);
  }
  nav button.active {
    background: var(--surface-2);
    font-weight: 600;
    color: var(--accent);
  }
  nav .toggle {
    align-self: flex-end;
    color: var(--muted);
  }
  nav.collapsed .toggle {
    align-self: center;
  }
  nav.collapsed .group-title,
  nav.collapsed .label {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
  nav.collapsed button {
    justify-content: center;
    position: relative;
  }
  nav.collapsed .count {
    position: absolute;
    top: 0;
    right: 2px;
    font-size: 0.7rem;
  }
  nav.collapsed .group + .group {
    border-top: 1px solid var(--border);
    padding-top: 0.6rem;
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
