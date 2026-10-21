<script lang="ts">
  // Change evidence: what changed since a release tag or the last commit (semantic diff).
  import { api, ApiError, download } from '../api'
  import { tr, type Key } from '../i18n'
  import { app } from '../state.svelte'
  import { COLLECTIONS, type Collection } from '../types'
  import RiskBadge from './RiskBadge.svelte'

  type Change = 'added' | 'removed' | 'changed'
  type ObjectChange = {
    collection: Collection
    id: string
    title: string
    change: Change
    old_id: string | null
    fields: string[]
    status: [string | null, string | null] | null
    risk: [number | null, number | null] | null
  }
  type Diff = {
    old_label: string
    config_fields: string[]
    models: { name: string; change: Change; meta_fields: string[]; objects: ObjectChange[] }[]
  }

  // default: the newest release tag; tags may arrive after this view opened
  let picked = $state<string | null>(null)
  const since = $derived(picked ?? app.tags[0]?.name ?? 'HEAD')
  let diff = $state<Diff | null>(null)
  let error = $state('')
  const lang = $derived(app.lang)
  const total = $derived(diff?.models.reduce((n, m) => n + m.objects.length, 0) ?? 0)

  $effect(() => {
    void app.model // recompute after every edit: the editor state is compared
    error = ''
    api<Diff>('GET', `/vcs/diff?since=${encodeURIComponent(since)}`)
      .then((d) => (diff = d))
      .catch((e) => {
        diff = null
        error = e instanceof ApiError ? e.message : String(e)
      })
  })

  const show = (o: ObjectChange) => {
    if (o.change !== 'removed') app.view = { kind: 'objects', collection: o.collection, selected: o.id }
  }
  const exportMd = () =>
    download(`/vcs/diff?since=${encodeURIComponent(since)}&format=md`, `changes-since-${since.replace(/[^\w.-]/g, '_')}.md`)
</script>

<section>
  <h1>{tr(lang, 'change_evidence')}</h1>
  <p class="muted help">{tr(lang, 'change_evidence_help')}</p>
  {#if !app.vcs}
    <p class="muted">{tr(lang, 'no_git')}</p>
  {:else}
    <div class="row">
      <label for="diff-since">{tr(lang, 'compare_with')}</label>
      <select id="diff-since" value={since} onchange={(e) => (picked = e.currentTarget.value)} data-testid="diff-since">
        {#each app.tags as tag}<option value={tag.name}>{tag.name} ({tag.date.slice(0, 10)})</option>{/each}
        <option value="HEAD">{tr(lang, 'last_commit')}</option>
      </select>
      <button onclick={exportMd} disabled={!diff}>{tr(lang, 'export_md')}</button>
    </div>
    {#if error}<p class="error" role="alert">{error}</p>{/if}
    {#if diff}
      <p data-testid="diff-total">{total} {tr(lang, 'changed_objects_total')}</p>
      {#if diff.config_fields.length}<p>{tr(lang, 'project_settings_changed')}: {diff.config_fields.join(', ')}</p>{/if}
      {#each diff.models as m (m.name)}
        <h2>{tr(lang, 'model')} {app.project?.models[m.name]?.title ?? m.name}{#if m.change !== 'changed'} ({tr(lang, `diff_${m.change}` as Key)}){/if}</h2>
        {#if m.meta_fields.length}<p class="muted">{tr(lang, 'meta_changed')}: {m.meta_fields.join(', ')}</p>{/if}
        {#each COLLECTIONS as c}
          {@const items = m.objects.filter((o) => o.collection === c)}
          {#if items.length}
            <h3>{tr(lang, c)}</h3>
            <ul class="changes">
              {#each items as o (o.id + o.change)}
                <li data-testid="diff-{o.id}">
                  <span class="badge {o.change}">{tr(lang, `diff_${o.change}` as Key)}</span>
                  {#if o.change === 'removed'}<strong>{o.id}</strong>{:else}<button class="link" onclick={() => show(o)}><strong>{o.id}</strong></button>{/if}
                  {o.title}
                  {#if o.old_id}<span class="muted">({tr(lang, 'formerly')} {o.old_id})</span>{/if}
                  {#if o.fields.length}<span class="muted">· {o.fields.join(', ')}</span>{/if}
                  {#if o.status}<span>· {tr(lang, 'status')}: {o.status[0] ?? '–'} → <strong>{o.status[1] ?? '–'}</strong></span>{/if}
                  {#if o.risk && o.risk[0] !== o.risk[1]}
                    <span>· {tr(lang, 'risk')}: <RiskBadge risk={o.risk[0]} /> → <RiskBadge risk={o.risk[1]} /></span>
                  {/if}
                </li>
              {/each}
            </ul>
          {/if}
        {/each}
      {:else}
        <p class="muted">{tr(lang, 'no_changes')}</p>
      {/each}
    {/if}
  {/if}
</section>

<style>
  h1 {
    font-size: 1.3rem;
    margin-top: 0;
  }
  h2 {
    font-size: 1.05rem;
    margin-top: 1.5rem;
  }
  h3 {
    font-size: 0.95rem;
    margin: 0.75rem 0 0.25rem;
  }
  .help {
    max-width: 75ch;
  }
  .row {
    display: flex;
    gap: 0.6rem;
    align-items: center;
    flex-wrap: wrap;
  }
  .row select {
    width: auto;
  }
  .changes {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 0.3rem;
  }
  .badge {
    display: inline-block;
    min-width: 5.5rem;
    text-align: center;
    padding: 0.05rem 0.45rem;
    border-radius: var(--radius);
    color: var(--risk-text);
  }
  .badge.added {
    background: var(--risk-1);
  }
  .badge.changed {
    background: var(--risk-3);
  }
  .badge.removed {
    background: var(--risk-5);
  }
  .link {
    border: none;
    background: none;
    color: var(--accent);
    padding: 0;
  }
</style>
