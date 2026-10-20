<script lang="ts">
  import CircleHelp from '@lucide/svelte/icons/circle-help'
  import { GLOSSARY, type Term } from '../glossary'
  import { tr } from '../i18n'
  import { app } from '../state.svelte'

  let { term }: { term: Term } = $props()
  const id = $props.id()
  const entry = $derived(GLOSSARY[term][app.lang])
</script>

<!-- Native popover: Esc and outside click close it, no positioning script needed. -->
<button
  type="button"
  class="info"
  popovertarget="info-{id}"
  aria-label="{tr(app.lang, 'explain')}: {entry.title}"
  title="{tr(app.lang, 'explain')}: {entry.title}"
  data-testid="info-{term}"
>
  <CircleHelp size={15} strokeWidth={2} aria-hidden="true" />
</button>
<div popover id="info-{id}" class="pop" role="note" data-testid="info-pop-{term}">
  <strong>{entry.title}</strong>
  <p>{entry.text}</p>
  <button type="button" popovertarget="info-{id}" popovertargetaction="hide">{tr(app.lang, 'close')}</button>
</div>

<style>
  .info {
    display: inline-grid;
    place-items: center;
    vertical-align: middle;
    width: 22px;
    height: 22px;
    margin-left: 0.2rem;
    padding: 0;
    border: none;
    border-radius: 50%;
    background: none;
    color: var(--accent);
    cursor: help;
  }
  .info:hover {
    background: var(--surface-2);
  }
  .pop {
    max-width: min(30rem, calc(100vw - 2rem));
    padding: 1rem 1.15rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--text);
    box-shadow: 0 12px 32px rgb(0 0 0 / 0.22);
    font-weight: normal;
    font-size: 14px;
    text-align: left;
  }
  .pop::backdrop {
    background: rgb(0 0 0 / 0.15);
  }
  .pop p {
    margin: 0.4rem 0 0.8rem;
    line-height: 1.55;
    max-width: 65ch;
  }
</style>
