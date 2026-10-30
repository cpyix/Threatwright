<script lang="ts">
  // listens_on of a process or device: protocol, port (unix: socket path) and interfaces.
  import { tr } from '../i18n'
  import { app } from '../state.svelte'

  type Listener = { protocol: 'tcp' | 'udp' | 'unix'; port?: number; path?: string; interfaces?: string }
  let { id, value = [], onchange }: { id: string; value: Listener[]; onchange: (v: Listener[]) => void } = $props()
  const lang = $derived(app.lang)

  function update(n: number, patch: Partial<Listener>) {
    const next = value.map((x, i) => (i === n ? { ...x, ...patch } : x))
    const x = next[n]
    // a unix socket has a path, tcp/udp a port
    if (x.protocol === 'unix') delete x.port
    else delete x.path
    onchange(next)
  }

  function address(n: number, raw: string) {
    const x = value[n]
    update(n, x.protocol === 'unix' ? { path: raw || undefined } : { port: raw === '' ? undefined : Number(raw) })
  }
</script>

<div class="listeners" role="group" aria-labelledby="{id}-label" data-testid="listeners">
  {#each value as x, n (n)}
    <div class="row">
      <select value={x.protocol} onchange={(e) => update(n, { protocol: e.currentTarget.value as Listener['protocol'] })} aria-label="Protocol">
        <option value="tcp">tcp</option>
        <option value="udp">udp</option>
        <option value="unix">unix</option>
      </select>
      <input
        value={x.protocol === 'unix' ? (x.path ?? '') : (x.port ?? '')}
        inputmode={x.protocol === 'unix' ? 'text' : 'numeric'}
        onchange={(e) => address(n, e.currentTarget.value.trim())}
        aria-label={tr(lang, 'listener_port_or_path')}
        placeholder={x.protocol === 'unix' ? '/run/….sock' : '502'}
      />
      <input
        value={x.interfaces ?? 'all'}
        list="{id}-interfaces"
        onchange={(e) => update(n, { interfaces: e.currentTarget.value.trim() || 'all' })}
        aria-label={tr(lang, 'listener_interfaces')}
      />
      <button type="button" onclick={() => onchange(value.filter((_, i) => i !== n))} aria-label={tr(lang, 'remove')}>×</button>
    </div>
  {/each}
  <datalist id="{id}-interfaces"><option value="all"></option><option value="loopback"></option></datalist>
  <button type="button" onclick={() => onchange([...value, { protocol: 'tcp', interfaces: 'all' }])} data-testid="listener-add">+ {tr(lang, 'listener_add')}</button>
</div>

<style>
  .row {
    display: grid;
    grid-template-columns: 5rem 1fr 1fr auto;
    gap: 0.3rem;
    margin-bottom: 0.3rem;
  }
</style>
