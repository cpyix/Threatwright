<script lang="ts">
  import { tr, type Key } from '../i18n'
  import { app, type HistoryEntry } from '../state.svelte'

  let entries = $state<HistoryEntry[]>([])
  let busy = $state(false)
  const lang = $derived(app.lang)
  const SHOWN = ['elements', 'flows', 'assets', 'threats', 'measures'] as const

  $effect(() => {
    void app.lastAutosave // reload when a new autosave arrived
    void app.project
    app.history().then((h) => (entries = h.entries)).catch(() => (entries = []))
  })

  const when = (iso: string) =>
    new Date(iso).toLocaleString(lang === 'de' ? 'de-DE' : 'en-GB', { dateStyle: 'medium', timeStyle: 'medium' })

  async function restore(id: string) {
    busy = true
    try {
      await app.restoreVersion(id)
    } finally {
      busy = false
    }
  }
</script>

<section>
  <h1>{tr(lang, 'history')}</h1>
  <p class="muted help">{tr(lang, 'history_help')}</p>
  {#if entries.length === 0}
    <p class="muted">{tr(lang, 'history_empty')}</p>
  {:else}
    <ol class="versions" data-testid="versions">
      {#each entries as e (e.id)}
        <li class="kind-{e.kind}" data-testid="version-{e.kind}">
          <span class="dot" aria-hidden="true"></span>
          <div class="what">
            <strong>{tr(lang, `history_${e.kind}` as Key)}</strong>
            <time datetime={e.time}>{when(e.time)}</time>
            <span class="muted counts">
              {SHOWN.map((c) => `${e.counts[c] ?? 0} ${tr(lang, c)}`).join(' · ')}
            </span>
          </div>
          <button onclick={() => restore(e.id)} disabled={busy} data-testid="restore-{e.id}">{tr(lang, 'restore')}</button>
        </li>
      {/each}
    </ol>
  {/if}
</section>

<style>
  h1 {
    font-size: 1.3rem;
    margin-top: 0;
  }
  .help {
    max-width: 70ch;
  }
  .versions {
    max-width: 52rem;
    list-style: none;
    padding: 0;
    margin: 1rem 0 0;
    border-left: 2px solid var(--border);
  }
  li {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    padding: 0.55rem 0.75rem 0.55rem 0;
    position: relative;
  }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-left: -6px;
    background: var(--muted);
    flex: none;
  }
  .kind-save .dot {
    background: var(--ok);
  }
  .kind-auto .dot {
    background: var(--surface);
    border: 2px solid var(--accent);
  }
  .what {
    flex: 1;
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 0.75rem;
    align-items: baseline;
  }
  time {
    font-variant-numeric: tabular-nums;
  }
  .counts {
    flex-basis: 100%;
    font-size: 0.9em;
  }
</style>
