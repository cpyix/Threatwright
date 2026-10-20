<script lang="ts">
  import type { NodeProps } from '@xyflow/svelte'
  import Pencil from '@lucide/svelte/icons/pencil'
  import X from '@lucide/svelte/icons/x'
  import { tr } from '../../i18n'
  import { app } from '../../state.svelte'

  type Data = { id: string; text: string; editing: boolean; onchange: (text: string) => void }
  let { data, selected }: NodeProps & { data: Data } = $props()
  // svelte-ignore state_referenced_locally (opens in edit mode once, when just added)
  let editing = $state(data.editing)
  // svelte-ignore state_referenced_locally (the field keeps its own draft while editing)
  let draft = $state(data.text)

  function edit() {
    draft = data.text
    editing = true
  }

  function commit() {
    if (!editing) return
    editing = false
    // an empty note is removed; unchanged text needs no save
    if (draft !== data.text || !draft.trim()) data.onchange(draft)
  }

  function onkeydown(e: KeyboardEvent) {
    e.stopPropagation() // keep Backspace, arrows etc. inside the text field
    if (e.key === 'Escape') {
      draft = data.text
      editing = false
      if (!data.text.trim()) data.onchange('')
    } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      commit()
    }
  }

  const focus = (el: HTMLTextAreaElement) => el.focus()
</script>

<div class="note" class:selected data-testid="note-{data.id}" ondblclick={edit} role="note">
  {#if editing}
    <textarea
      class="nodrag nowheel"
      bind:value={draft}
      placeholder={tr(app.lang, 'note_placeholder')}
      aria-label={tr(app.lang, 'edit_note')}
      onblur={commit}
      {onkeydown}
      use:focus
      data-testid="note-input"
    ></textarea>
  {:else}
    <span class="text">{data.text}</span>
  {/if}
  {#if selected && !editing}
    <span class="actions nodrag">
      <button type="button" onclick={edit} title={tr(app.lang, 'edit_note')} aria-label={tr(app.lang, 'edit_note')}>
        <Pencil size={13} aria-hidden="true" />
      </button>
      <button
        type="button"
        onclick={() => data.onchange('')}
        title={tr(app.lang, 'delete_note')}
        aria-label={tr(app.lang, 'delete_note')}
        data-testid="note-delete"
      >
        <X size={13} aria-hidden="true" />
      </button>
    </span>
  {/if}
</div>

<style>
  .note {
    position: relative;
    min-width: 8rem;
    max-width: 22rem;
    padding: 6px 8px;
    background: var(--note-bg);
    border: 1px solid var(--note-border);
    border-radius: 4px;
    color: var(--text);
    font-size: 12px;
    box-shadow: 0 1px 2px rgb(0 0 0 / 0.12);
  }
  .selected {
    outline: 2px solid var(--focus);
    outline-offset: 2px;
  }
  .text {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  textarea {
    width: 16rem;
    min-height: 4rem;
    font: inherit;
    background: var(--surface);
    color: var(--text);
    resize: both;
  }
  .actions {
    position: absolute;
    top: -12px;
    right: -12px;
    display: flex;
    gap: 2px;
  }
  .actions button {
    display: grid;
    place-items: center;
    width: 22px;
    height: 22px;
    padding: 0;
    border: 1px solid var(--border);
    border-radius: 50%;
    background: var(--surface);
    color: var(--text);
    cursor: pointer;
  }
</style>
