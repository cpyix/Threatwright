<script lang="ts">
  // SBOMs and vulnerability statements (CycloneDX VEX, CSAF) of the project, findings per element.
  import { api, ApiError, upload } from '../api'
  import { tr, type Key } from '../i18n'
  import { app } from '../state.svelte'
  import type { ModelPayload, Obj } from '../types'

  type Finding = {
    vuln: string
    element: string
    purl: string
    state: 'affected' | 'under_investigation' | 'fixed' | 'not_affected'
    sources: string[]
    detail: string | null
    threats: string[]
    open: boolean
  }

  let found = $state<Finding[]>([])
  let files = $state<FileList>()
  let kind = $state<'sbom' | 'vulnerabilities'>('sbom')
  let note = $state('')
  const lang = $derived(app.lang)
  const untreated = $derived(found.filter((f) => f.open && !f.threats.length).length)

  async function load() {
    try {
      found = await api<Finding[]>('GET', `/models/${app.modelName}/vulnerabilities`)
    } catch (e) {
      note = e instanceof ApiError ? e.message : String(e)
    }
  }

  $effect(() => {
    void app.model
    load()
  })

  async function send() {
    note = ''
    const file = files?.[0]
    if (!file) return
    try {
      const query = new URLSearchParams({ name: file.name, kind })
      const r = await upload<{ written: string; replaced: boolean; count: number }>(`/sbom/upload?${query}`, file)
      note = `${tr(lang, r.replaced ? 'sbom_replaced' : 'imported')}: ${r.written} (${r.count})`
      await app.refreshSbom()
      await app.afterChange()
      await load()
    } catch (e) {
      note = e instanceof ApiError ? e.message : String(e)
    }
  }

  const title = (id: string) => app.objects('elements').find((e) => e.id === id)?.title ?? ''

  async function createThreat(f: Finding) {
    const name = f.purl.replace(/^pkg:[^/]+\//, '')
    const body = {
      title: `${tr(lang, 'vuln_threat_title')} ${f.vuln}: ${name}`,
      targets: [f.element],
      vulnerabilities: [f.vuln],
      cyber_cause: true, // a known vulnerability is exploitable by an attacker: rule 3.3
      scenario: `${f.vuln} (${f.purl})${f.detail ? `: ${f.detail}` : ''}`,
      cra_refs: ['AI-I-2-a', 'AI-II-2'],
      status: 'identified',
      stride: [],
      assessment: {},
    }
    const r = await api<{ object: Obj; model: ModelPayload }>('POST', `/models/${app.modelName}/threats`, body)
    await app.afterChange(r.model)
    app.view = { kind: 'objects', collection: 'threats', selected: r.object.id }
  }

  const open = (id: string) => (app.view = { kind: 'objects', collection: 'threats', selected: id })
</script>

<section>
  <h1>{tr(lang, 'vulnerabilities')}</h1>
  <p class="muted help">{tr(lang, 'vulnerabilities_help')}</p>

  <h2>{tr(lang, 'sbom_files')}</h2>
  {#if app.sbom.sboms.length}
    <table>
      <thead><tr><th>{tr(lang, 'file')}</th><th>{tr(lang, 'components')}</th><th>{tr(lang, 'elements')}</th></tr></thead>
      <tbody>
        {#each app.sbom.sboms as s (s.file)}
          <tr><td>{s.file}</td><td>{s.components}</td><td>{s.elements.join(', ') || tr(lang, 'sbom_unused')}</td></tr>
        {/each}
      </tbody>
    </table>
  {:else}
    <p class="muted">{tr(lang, 'sbom_none')}</p>
  {/if}
  {#if app.sbom.vulnerability_files.length}
    <p>{tr(lang, 'vuln_files')}: {app.sbom.vulnerability_files.join(', ')}</p>
  {/if}
  {#each app.sbom.issues as issue}<p class="error">{issue}</p>{/each}
  <form class="row" onsubmit={(e) => { e.preventDefault(); send() }}>
    <input type="file" accept=".json,application/json" bind:files required aria-label={tr(lang, 'file')} data-testid="sbom-file" />
    <select bind:value={kind} aria-label={tr(lang, 'import_as')}>
      <option value="sbom">{tr(lang, 'sbom_kind')}</option>
      <option value="vulnerabilities">{tr(lang, 'vuln_kind')}</option>
    </select>
    <button type="submit" data-testid="sbom-upload">{tr(lang, 'import')}</button>
  </form>
  {#if note}<p role="status">{note}</p>{/if}

  <h2>{tr(lang, 'vuln_findings')}</h2>
  {#if found.length === 0}
    <p class="muted">{tr(lang, 'vuln_none')}</p>
  {:else}
    <p data-testid="vuln-untreated" class={untreated ? 'error' : 'ok'}>{untreated} {tr(lang, 'vuln_untreated')}</p>
    <table data-testid="vuln-table">
      <thead>
        <tr><th>{tr(lang, 'vulnerability')}</th><th>{tr(lang, 'elements')}</th><th>{tr(lang, 'component')}</th><th>{tr(lang, 'status')}</th><th>{tr(lang, 'threats')}</th></tr>
      </thead>
      <tbody>
        {#each found as f (`${f.vuln} ${f.element} ${f.purl}`)}
          <tr data-testid="vuln-{f.vuln}">
            <td><strong>{f.vuln}</strong>{#if f.detail}<br /><span class="muted small">{f.detail}</span>{/if}</td>
            <td>{f.element} {title(f.element)}</td>
            <td class="purl">{f.purl}<br /><span class="muted small">{f.sources.join(', ')}</span></td>
            <td><span class="badge" class:open={f.open}>{tr(lang, `vuln_${f.state}` as Key)}</span></td>
            <td>
              {#each f.threats as id}<button class="link" onclick={() => open(id)}>{id}</button> {/each}
              {#if f.open && !f.threats.length}
                <button onclick={() => createThreat(f)} data-testid="vuln-threat-{f.vuln}">{tr(lang, 'vuln_create_threat')}</button>
              {/if}
            </td>
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
  h2 {
    font-size: 1.05rem;
    margin-top: 1.5rem;
  }
  .help {
    max-width: 75ch;
  }
  .row {
    display: flex;
    gap: 0.5rem;
    margin: 0.5rem 0;
    flex-wrap: wrap;
  }
  .row input {
    flex: 1;
  }
  .row select {
    width: auto;
  }
  .small {
    font-size: 0.85em;
  }
  .purl {
    word-break: break-all;
  }
  .badge {
    display: inline-block;
    padding: 0.05rem 0.45rem;
    border-radius: var(--radius);
    background: var(--risk-1);
    color: var(--risk-text);
    white-space: nowrap;
  }
  .badge.open {
    background: var(--risk-5);
  }
  .link {
    border: none;
    background: none;
    color: var(--accent);
    padding: 0;
  }
</style>
