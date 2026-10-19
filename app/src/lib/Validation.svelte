<script lang="ts">
  import { tr } from '../i18n'
  import { app } from '../state.svelte'
  import { COLLECTIONS, type Collection, type Issue } from '../types'

  const lang = $derived(app.lang)
  const sorted = $derived(
    [...app.issues].sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'error' ? -1 : 1)),
  )

  function target(issue: Issue): Collection | null {
    const part = issue.file.split('/')[2]
    return (COLLECTIONS as readonly string[]).includes(part) ? (part as Collection) : null
  }

  function go(issue: Issue) {
    const collection = target(issue)
    if (!collection || !issue.object) return
    if (issue.model) app.modelName = issue.model
    app.view = { kind: 'objects', collection, selected: issue.object }
  }
</script>

<section>
  <h1>{tr(lang, 'validation')}</h1>
  {#if sorted.length === 0}
    <p class="ok">{tr(lang, 'no_issues')}</p>
  {:else}
    <table data-testid="issues">
      <tbody>
        {#each sorted as issue}
          <tr>
            <td class={issue.severity}>{issue.severity === 'error' ? tr(lang, 'errors') : tr(lang, 'warnings')}</td>
            <td>
              {#if target(issue) && issue.object}
                <button class="rowlink" onclick={() => go(issue)}>{issue.object}</button>
              {:else}
                <span class="muted">{issue.file}</span>
              {/if}
            </td>
            <td><code>{issue.location}</code></td>
            <td>{issue.message} <span class="muted">({issue.code})</span></td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</section>

<style>
  h1 {
    font-size: 1.3rem;
    margin-top: 0;
  }
  .rowlink {
    border: none;
    background: none;
    padding: 0;
    color: var(--accent);
    font-weight: 600;
  }
</style>
