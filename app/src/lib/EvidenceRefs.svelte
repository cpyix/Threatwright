<script lang="ts">
  // Evidence of a measure: links, or files stored in the project folder evidence/.
  import { ApiError, download, upload } from '../api'
  import { tr } from '../i18n'
  import { app } from '../state.svelte'

  let { id, value = [], onchange }: { id: string; value: string[]; onchange: (v: string[]) => void } = $props()

  let link = $state('')
  let error = $state('')
  const lang = $derived(app.lang)
  const isLink = (ref: string) => /^https?:\/\//.test(ref)

  function addLink() {
    error = ''
    if (!isLink(link.trim())) {
      error = tr(lang, 'evidence_link_hint')
      return
    }
    onchange([...value, link.trim()])
    link = ''
  }

  async function addFile(e: Event & { currentTarget: HTMLInputElement }) {
    error = ''
    const file = e.currentTarget.files?.[0]
    if (!file) return
    try {
      const r = await upload<{ ref: string }>(`/evidence/upload?${new URLSearchParams({ name: file.name })}`, file)
      onchange([...value, r.ref])
    } catch (err) {
      error = err instanceof ApiError ? err.message : String(err)
    }
    e.currentTarget.value = ''
  }

  const open = (ref: string) => download(`/evidence?${new URLSearchParams({ ref })}`, ref.split('/').pop() ?? ref)
</script>

<div class="evidence" role="group" aria-labelledby="{id}-label" data-testid="evidence-refs">
  {#each value as ref, n (ref)}
    <div class="item">
      {#if isLink(ref)}
        <a href={ref} target="_blank" rel="noopener noreferrer">{ref}</a>
      {:else}
        <button type="button" class="link" onclick={() => open(ref)}>{ref}</button>
      {/if}
      <button type="button" onclick={() => onchange(value.filter((_, i) => i !== n))} aria-label="{tr(lang, 'remove')} {ref}">×</button>
    </div>
  {/each}
  <div class="add">
    <input
      type="url"
      bind:value={link}
      placeholder="https://…"
      aria-label={tr(lang, 'evidence_link')}
      onkeydown={(e) => {
        if (e.key === 'Enter') {
          e.preventDefault()
          addLink()
        }
      }}
      data-testid="evidence-link"
    />
    <button type="button" onclick={addLink}>{tr(lang, 'evidence_add_link')}</button>
    <label class="file">
      <span>{tr(lang, 'evidence_add_file')}</span>
      <input type="file" onchange={addFile} data-testid="evidence-file" />
    </label>
  </div>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
</div>

<style>
  .evidence {
    display: grid;
    gap: 0.3rem;
  }
  .item {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    word-break: break-all;
  }
  .add {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
  }
  .add input[type='url'] {
    flex: 1;
    min-width: 12rem;
  }
  .file input {
    width: auto;
  }
  .file {
    display: flex;
    gap: 0.3rem;
    align-items: center;
  }
  .link {
    border: none;
    background: none;
    color: var(--accent);
    padding: 0;
    text-align: left;
  }
</style>
