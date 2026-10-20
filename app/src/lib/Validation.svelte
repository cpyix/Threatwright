<script lang="ts">
  import { tr } from '../i18n'
  import { RULES } from '../rule-text'
  import { app } from '../state.svelte'
  import { COLLECTIONS, type Collection, type Issue } from '../types'

  const lang = $derived(app.lang)
  // One group per rule, errors first: dozens of coverage gaps collapse into one line.
  const groups = $derived.by(() => {
    const by = new Map<string, Issue[]>()
    for (const i of app.issues) by.set(`${i.severity}:${i.code}`, [...(by.get(`${i.severity}:${i.code}`) ?? []), i])
    return [...by.values()].sort((a, b) =>
      a[0].severity === b[0].severity ? b.length - a.length : a[0].severity === 'error' ? -1 : 1,
    )
  })

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
  {#if groups.length === 0}
    <p class="ok">{tr(lang, 'no_issues')}</p>
  {:else}
    <div data-testid="issues">
      {#each groups as list (list[0].severity + list[0].code)}
        {@const first = list[0]}
        <details class="group" open={first.severity === 'error'} data-testid="issue-group-{first.code}">
          <summary>
            <span class="sev {first.severity}">{tr(lang, first.severity === 'error' ? 'error_one' : 'warning_one')}</span>
            <span class="what">{RULES[lang][first.code] ?? first.message}</span>
            <span class="n">{list.length}</span>
          </summary>
          <table>
            <tbody>
              {#each list as issue}
                <tr>
                  <td>
                    {#if target(issue) && issue.object}
                      <button class="rowlink" onclick={() => go(issue)}>{issue.object}</button>
                    {:else}
                      <span class="muted">{issue.file}</span>
                    {/if}
                  </td>
                  <td><code>{issue.location}</code></td>
                  <td class="muted">{issue.message}</td>
                </tr>
              {/each}
            </tbody>
          </table>
          <p class="muted small">{tr(lang, 'rule')}: <code>{first.code}</code></p>
        </details>
      {/each}
    </div>
  {/if}
</section>

<style>
  h1 {
    font-size: 1.3rem;
    margin-top: 0;
  }
  .group {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    margin-bottom: 0.5rem;
    padding: 0.5rem 0.75rem;
  }
  summary {
    display: flex;
    gap: 0.75rem;
    align-items: baseline;
    cursor: pointer;
  }
  .sev {
    font-weight: 600;
    flex: none;
  }
  .what {
    flex: 1;
  }
  .n {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    color: var(--muted);
  }
  .group table {
    margin-top: 0.5rem;
  }
  .rowlink {
    border: none;
    background: none;
    padding: 0;
    color: var(--accent);
    font-weight: 600;
  }
</style>
