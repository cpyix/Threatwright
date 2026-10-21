// Where elements run and which boundary a flow crosses; mirrors src/threatwright/topology.py.
import type { Obj } from './types'

export type Boundary = 'zone' | 'privilege' | null

/** Hosts of `el` along runs_on, nearest first; stops at a missing host or a cycle. */
export function hostChain(byId: Map<string, Obj>, el: Obj): Obj[] {
  const chain: Obj[] = []
  const seen = new Set([el.id])
  let current = el
  while (current.runs_on && !seen.has(current.runs_on) && byId.has(current.runs_on)) {
    current = byId.get(current.runs_on)!
    seen.add(current.id)
    chain.push(current)
  }
  return chain
}

/** Own zone, else the zone of the nearest host that has one. */
export function effectiveZone(byId: Map<string, Obj>, el: Obj): string | null {
  return [el, ...hostChain(byId, el)].find((e) => e.zone)?.zone ?? null
}

/** Rights context on the host, or null without host or privilege. */
export function context(el: Obj): string | null {
  if (!el.runs_on || !el.privilege) return null
  return [el.runs_on, el.privilege.level, el.privilege.account ?? ''].join('|')
}

export function boundary(byId: Map<string, Obj>, flow: Obj): Boundary {
  const src = byId.get(flow.source)
  const tgt = byId.get(flow.target)
  if (!src || !tgt) return null
  if (effectiveZone(byId, src) !== effectiveZone(byId, tgt)) return 'zone'
  const a = context(src)
  const b = context(tgt)
  return a && b && src.runs_on === tgt.runs_on && a !== b ? 'privilege' : null
}
