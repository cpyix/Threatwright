<script lang="ts">
  import { tr } from '../i18n'
  import { app } from '../state.svelte'
  import type { Evaluation, ThreatEvaluation } from '../types'
  import Info from './Info.svelte'
  import RiskBadge from './RiskBadge.svelte'

  let {
    prefix,
    value,
    evaluation,
    suggestion,
    set,
  }: {
    prefix: 'assessment' | 'residual'
    value: Record<string, any>
    evaluation: Evaluation | null | undefined
    suggestion?: ThreatEvaluation['suggestion']
    set: (path: string, v: any) => void
  } = $props()

  const lang = $derived(app.lang)
  const indicators = ['interface', 'access', 'user'] as const
  const levels = $derived(Object.entries(app.method?.impact_levels.levels ?? {}))
  const factor = (f: string) => Number(f).toLocaleString(lang === 'de' ? 'de-DE' : 'en-GB')
</script>

<fieldset class="assessment" data-testid="{prefix}-panel">
  <legend>
    {tr(lang, prefix === 'assessment' ? 'assessment' : 'residual')}
    {#if prefix === 'residual'}<Info term="residual" />{/if}
  </legend>
  <p class="env-head">{tr(lang, 'environment')} <Info term="environment" /></p>
  <div class="grid">
    {#each indicators as name}
      <label>
        {tr(lang, name)}
        <select
          value={value?.[name] ?? ''}
          onchange={(e) => set(`${prefix}.${name}`, e.currentTarget.value)}
          data-testid="{prefix}-{name}"
        >
          <option value="">–</option>
          {#each Object.entries(app.method?.[name].values ?? {}) as [key, v]}
            <option value={key}>{v[lang]} ({factor(v.factor)})</option>
          {/each}
        </select>
        {#if value?.[name] && app.method?.[name].values[value[name]]?.help?.[lang]}
          <small class="muted">{app.method[name].values[value[name]].help?.[lang]} (TR {app.method[name].source})</small>
        {/if}
      </label>
    {/each}
  </div>

  <div class="impact" role="group" aria-label={tr(lang, 'impact')}>
    <span>{tr(lang, 'impact')} <Info term="impact" /></span>
    {#each levels as [level, l]}
      <button
        type="button"
        aria-pressed={value?.impact === Number(level)}
        class:selected={value?.impact === Number(level)}
        title={l[lang]}
        data-testid="{prefix}-impact-{level}"
        onclick={() => set(`${prefix}.impact`, Number(level))}>{level}</button
      >
    {/each}
    {#if suggestion && prefix === 'assessment'}
      <button
        type="button"
        class="link"
        onclick={() => set('assessment.impact', suggestion.impact)}
        data-testid="impact-suggestion"
      >
        {tr(lang, 'suggestion')} {suggestion.impact} {tr(lang, 'from')}
        {suggestion.asset_id} ({suggestion.dimension})
      </button>
    {/if}
  </div>

  <output class="result" aria-live="polite">
    <span>{tr(lang, 'exposure')}: <strong>{evaluation?.exposure ?? '–'}</strong> <Info term="exposure" /></span>
    <span>{tr(lang, 'risk')}: <RiskBadge risk={evaluation?.risk} /></span>
    {#if evaluation?.acceptable === true}
      <span class="ok" data-testid="{prefix}-verdict">{tr(lang, 'acceptable')}</span>
    {:else if evaluation?.acceptable === false}
      <span class="error" data-testid="{prefix}-verdict">{tr(lang, 'to_treat')}</span>
    {/if}
  </output>

  <label>
    {tr(lang, 'rationale')}
    <textarea
      value={value?.rationale ?? ''}
      oninput={(e) => set(`${prefix}.rationale`, e.currentTarget.value)}
    ></textarea>
  </label>
  {#if prefix === 'assessment'}
    <p class="muted note">
      {tr(lang, app.method?.risk_matrix.matrix_row_from_exposure === 'literal' ? 'matrix_literal' : 'matrix_inverted')}
    </p>
  {/if}
</fieldset>

<style>
  .assessment {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.75rem;
    display: grid;
    gap: 0.6rem;
    background: var(--surface-2);
  }
  .env-head {
    margin: 0 0 0.2rem;
    font-weight: 600;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
    gap: 0.5rem;
  }
  label {
    display: grid;
    gap: 0.2rem;
  }
  .impact {
    display: flex;
    gap: 0.35rem;
    align-items: center;
    flex-wrap: wrap;
  }
  .impact .selected {
    background: var(--accent);
    color: var(--accent-text);
    border-color: var(--accent);
  }
  .link {
    border: none;
    background: none;
    color: var(--accent);
    text-decoration: underline;
  }
  .result {
    display: flex;
    gap: 1.25rem;
    align-items: center;
    flex-wrap: wrap;
  }
  .note {
    margin: 0;
    font-size: 0.9em;
  }
</style>
