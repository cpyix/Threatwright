<script lang="ts">
  import { Panel } from '@xyflow/svelte'
  import { tr } from '../../i18n'
  import { app } from '../../state.svelte'
  import Info from '../Info.svelte'

  const lang = $derived(app.lang)
  const levels = $derived(Object.entries(app.method?.risk_levels.levels ?? {}))
</script>

<Panel position="bottom-right">
  <details class="legend" data-testid="legend">
    <summary>{tr(lang, 'legend')}</summary>
    <ul>
      {#each levels as [n, name]}
        <li><span class="swatch risk-{n}"></span>{tr(lang, 'risk')} {n} {name[lang]}</li>
      {/each}
      <li><span class="zone"></span>{tr(lang, 'legend_zone')} <Info term="zone" /></li>
      <li>
        <svg width="28" height="8" aria-hidden="true"><line x1="0" y1="4" x2="28" y2="4" class="cross" /></svg>
        {tr(lang, 'legend_cross_zone')}
      </li>
      <li>
        <svg width="28" height="8" aria-hidden="true"><line x1="0" y1="4" x2="28" y2="4" class="cross-privilege" /></svg>
        {tr(lang, 'boundary_privilege')}
      </li>
      <li>
        <svg width="28" height="8" aria-hidden="true"><line x1="0" y1="4" x2="28" y2="4" class="high" /></svg>
        {tr(lang, 'legend_high_risk_flow')}
      </li>
    </ul>
  </details>
</Panel>

<style>
  .legend {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.35rem 0.6rem;
    font-size: 12px;
    box-shadow: 0 2px 8px rgb(0 0 0 / 0.12);
  }
  summary {
    cursor: pointer;
    font-weight: 600;
  }
  ul {
    list-style: none;
    margin: 0.35rem 0 0;
    padding: 0;
    display: grid;
    gap: 0.2rem;
  }
  li {
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }
  .swatch,
  .zone {
    width: 28px;
    height: 12px;
    border-radius: 3px;
    border: 1px solid var(--text);
    flex: none;
  }
  .risk-1 { background: var(--risk-1); }
  .risk-2 { background: var(--risk-2); }
  .risk-3 { background: var(--risk-3); }
  .risk-4 { background: var(--risk-4); }
  .risk-5 { background: var(--risk-5); }
  .zone {
    border: 1.5px dashed var(--muted);
  }
  line {
    stroke: var(--text);
    stroke-width: 2;
  }
  .cross {
    stroke-dasharray: 7 4;
  }
  .cross-privilege {
    stroke-dasharray: 2 3;
  }
  .high {
    stroke: var(--error);
  }
</style>
