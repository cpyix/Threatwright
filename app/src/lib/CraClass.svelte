<script lang="ts">
  // Optional CRA classification for orientation: local state only, nothing is stored or reported.
  import { CATEGORIES_CRA, CLASS_NAME, CRA_TEXT, PROCEDURE, SCOPE_EXCLUSIONS } from '../cra-class'
  import { app } from '../state.svelte'

  const lang = $derived(app.lang)
  const t = $derived(CRA_TEXT[lang])
  const groups = ['I', 'II', 'critical'] as const

  let scope = $state('')
  let category = $state('')
  const cls = $derived(category === 'none' ? 'default' : CATEGORIES_CRA.find((x) => x.id === category)?.cls)
</script>

<p class="notice" role="note">{t.notice}</p>
<p class="muted">{t.skip}</p>

<fieldset class="card">
  <legend>{t.scope_q}</legend>
  <p>{t.scope_text}</p>
  <ul>{#each SCOPE_EXCLUSIONS as x}<li>{x[lang]}</li>{/each}</ul>
  <div class="answers">
    {#each ['yes', 'no', 'unsure'] as const as v}
      <label><input type="radio" name="cra-scope" value={v} bind:group={scope} /> {t[v]}</label>
    {/each}
  </div>
</fieldset>

<fieldset class="card">
  <legend>{t.category_q}</legend>
  <p class="muted">{t.category_hint}</p>
  {#each groups as g}
    <p class="group">{t[`class_${g}`]}</p>
    {#each CATEGORIES_CRA.filter((x) => x.cls === g) as x (x.id)}
      <label>
        <input type="radio" name="cra-category" value={x.id} bind:group={category} />
        <span>{x.label[lang]}{#if x.examples}{' '}<span class="muted">({x.examples[lang]})</span>{/if}</span>
      </label>
    {/each}
  {/each}
  <label class="none"><input type="radio" name="cra-category" value="none" bind:group={category} /> {t.none}</label>
</fieldset>

<div class="card result" data-testid="cra-result" aria-live="polite">
  <strong>{t.result}</strong>
  {#if scope === 'no'}
    <p>{t.out_of_scope}</p>
  {:else if cls}
    <p><strong>{CLASS_NAME[cls][lang]}</strong></p>
    <p>{PROCEDURE[cls][lang]}</p>
  {:else}
    <p class="muted">{t.pick}</p>
  {/if}
  <p>{t.same}</p>
</div>

<style>
  .notice {
    border-left: 4px solid var(--warning);
    background: var(--surface-2);
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius);
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.6rem 0.9rem;
    display: grid;
    gap: 0.35rem;
  }
  legend {
    font-weight: 600;
  }
  p,
  ul {
    margin: 0.2rem 0;
  }
  .answers {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1.25rem;
  }
  label {
    display: flex;
    gap: 0.5rem;
    align-items: start;
  }
  input {
    width: auto;
    margin-top: 0.2rem;
  }
  .group {
    font-weight: 600;
    margin-top: 0.5rem;
  }
  .none {
    margin-top: 0.5rem;
  }
  .result {
    border-color: var(--accent);
  }
</style>
