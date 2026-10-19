<script lang="ts">
  import { tr } from '../i18n'
  import { app } from '../state.svelte'
  import { COLLECTIONS } from '../types'
  import ModelMeta from './ModelMeta.svelte'
  import RiskBadge from './RiskBadge.svelte'

  const lang = $derived(app.lang)
  const threats = $derived(app.objects('threats').filter((t) => t.status !== 'rejected'))
  const risks = $derived(threats.map((t) => app.model?.evaluations[t.id]?.assessment.risk ?? null))
  const distribution = $derived([1, 2, 3, 4, 5].map((r) => risks.filter((x) => x === r).length))
  const maxBar = $derived(Math.max(1, ...distribution))
  const unassessed = $derived(risks.filter((r) => r == null).length)
  const errors = $derived(app.issues.filter((i) => i.severity === 'error' && i.model === app.modelName).length)
  const warnings = $derived(app.issues.filter((i) => i.severity === 'warning' && i.model === app.modelName).length)
  const assets = $derived(app.objects('assets'))
  const status = $derived([
    [tr(lang, 'assets_classified'), assets.filter((a) => a.asset_class).length, assets.length],
    [tr(lang, 'threats_assessed'), risks.filter((r) => r != null).length, threats.length],
    [
      tr(lang, 'threats_handled'),
      app.objects('threats').filter((t) => ['treated', 'accepted', 'rejected'].includes(t.status)).length,
      app.objects('threats').length,
    ],
  ] as [string, number, number][])
  const openQuestions = $derived(app.objects('questions').filter((q) => q.status !== 'answered').length)
</script>

<section>
  <h1>{app.model?.meta.title ?? tr(lang, 'overview')}</h1>
  <div class="cards">
    {#each COLLECTIONS as c}
      <button class="card" onclick={() => (app.view = { kind: 'objects', collection: c, selected: null })}>
        <strong>{app.objects(c).length}</strong>
        <span>{tr(lang, c)}</span>
      </button>
    {/each}
    <button class="card" onclick={() => (app.view = { kind: 'validation' })}>
      <strong class:error={errors > 0}>{errors}</strong>
      <span>{tr(lang, 'errors')} · {warnings} {tr(lang, 'warnings')}</span>
    </button>
  </div>

  <h2>{tr(lang, 'risk_distribution')}</h2>
  <div class="bars" role="list">
    {#each distribution as n, i}
      <div class="bar" role="listitem">
        <span class="label"><RiskBadge risk={i + 1} /></span>
        <span class="track"><span class="fill risk-{i + 1}" style:width="{(n / maxBar) * 100}%"></span></span>
        <span>{n}</span>
      </div>
    {/each}
    <div class="bar muted">{tr(lang, 'not_assessed')}: {unassessed}</div>
  </div>

  {#if app.vcs}
    <h2>{tr(lang, 'changes')}</h2>
    <label>
      {tr(lang, 'changes_since')}
      <select
        value={app.changedSince}
        onchange={(e) => {
          app.changedSince = e.currentTarget.value
          app.refreshChanges()
        }}
      >
        <option value="">{tr(lang, 'last_commit')}</option>
        {#each app.tags as tag}<option value={tag.name}>{tag.name} ({tag.date.slice(0, 10)})</option>{/each}
      </select>
    </label>
    <p>{app.changed.size} {tr(lang, 'changed_objects')}</p>
  {/if}

  <h2>{tr(lang, 'tr_status')}</h2>
  <ul class="status">
    {#each status as [text, done, total]}
      <li>
        <span class={done === total ? 'ok' : 'warning'}>{done === total ? '✓' : '•'}</span>
        {text}: {done}/{total}
      </li>
    {/each}
    <li><span class={openQuestions ? 'warning' : 'ok'}>{openQuestions ? '•' : '✓'}</span> {openQuestions} {tr(lang, 'open_questions')}</li>
  </ul>

  <ModelMeta />
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
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
    gap: 0.6rem;
  }
  .card {
    display: grid;
    text-align: left;
    padding: 0.75rem;
    background: var(--surface);
  }
  .card strong {
    font-size: 1.6rem;
  }
  .bars {
    display: grid;
    gap: 0.35rem;
    max-width: 36rem;
  }
  .bar {
    display: grid;
    grid-template-columns: 9rem 1fr 2rem;
    gap: 0.5rem;
    align-items: center;
  }
  .track {
    background: var(--surface-2);
    border-radius: 4px;
    height: 0.9rem;
  }
  .fill {
    display: block;
    height: 100%;
    border-radius: 4px;
  }
  .status {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 0.25rem;
  }
</style>
