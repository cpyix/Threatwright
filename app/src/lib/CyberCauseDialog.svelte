<script lang="ts">
  // Rule 3.3 "Is this a cyber risk?" asked for every new threat.
  import { api } from '../api'
  import { tr } from '../i18n'
  import { app } from '../state.svelte'
  import type { ModelPayload, Obj } from '../types'

  let dialog: HTMLDialogElement
  let rejecting = $state(false)
  let rationale = $state('')
  const lang = $derived(app.lang)
  const threat = $derived(app.objects('threats').find((t) => t.id === app.cyberCheck))

  $effect(() => {
    if (app.cyberCheck && dialog && !dialog.open) {
      rejecting = false
      rationale = tr(lang, 'reject_text')
      dialog.showModal()
    }
  })

  async function answer(update: Partial<Obj>) {
    if (!threat) return
    const r = await api<{ model: ModelPayload }>(
      'PUT',
      `/models/${app.modelName}/threats/${threat.id}`,
      { ...$state.snapshot(threat), ...update },
    )
    await app.afterChange(r.model)
    close()
  }

  function close() {
    app.cyberCheck = null
    dialog.close()
  }
</script>

<dialog bind:this={dialog} onclose={() => (app.cyberCheck = null)} aria-labelledby="cyber-q" data-testid="cyber-dialog">
  <h2 id="cyber-q">{tr(lang, 'cyber_question')}</h2>
  {#if threat}<p><strong>{threat.id}</strong> {threat.title}</p>{/if}
  <p class="muted">{tr(lang, 'cyber_help')}</p>
  {#if !rejecting}
    <div class="actions">
      <button class="primary" onclick={() => answer({ cyber_cause: true })} data-testid="cyber-yes">{tr(lang, 'cyber_yes')}</button>
      <button onclick={() => (rejecting = true)} data-testid="cyber-no">{tr(lang, 'cyber_no')}</button>
      <button onclick={close}>{tr(lang, 'cancel')}</button>
    </div>
  {:else}
    <label for="reject-why">{tr(lang, 'rejection_rationale')}</label>
    <textarea id="reject-why" bind:value={rationale}></textarea>
    <div class="actions">
      <button
        class="primary"
        disabled={!rationale.trim()}
        onclick={() => answer({ cyber_cause: false, status: 'rejected', rejection: { rationale } })}
        data-testid="cyber-reject">{tr(lang, 'reject')}</button
      >
      <button onclick={() => (rejecting = false)}>{tr(lang, 'cancel')}</button>
    </div>
  {/if}
</dialog>

<style>
  dialog {
    max-width: 34rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--text);
    padding: 1rem 1.25rem;
  }
  dialog::backdrop {
    background: rgb(0 0 0 / 0.4);
  }
  h2 {
    font-size: 1.1rem;
    margin-top: 0;
  }
  .actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.75rem;
  }
  textarea {
    margin-top: 0.25rem;
  }
</style>
