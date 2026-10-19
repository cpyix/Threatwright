<script lang="ts">
  import { app } from '../state.svelte'

  let { risk }: { risk: number | null | undefined } = $props()
  const text = $derived(
    risk ? (app.method?.risk_levels.levels[String(risk)]?.[app.lang] ?? String(risk)) : '–',
  )
</script>

{#if risk}
  <span class="risk risk-{risk}" data-testid="risk-badge">{risk} {text}</span>
{:else}
  <span class="muted">–</span>
{/if}
