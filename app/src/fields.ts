import { label, type Key } from './i18n'
import { assetClassLabel } from './setup-text'
import { app } from './state.svelte'
import type { Collection, Obj } from './types'

export type Option = { value: string; label: string }
export type FieldType = 'text' | 'longtext' | 'select' | 'multi' | 'bool' | 'tristate' | 'number' | 'date'

export interface Field {
  key: string // dotted path into the object
  label: Key
  type: FieldType
  options?: () => Option[]
  required?: boolean
}

const STRIDE = ['S', 'T', 'R', 'I', 'D', 'E']

const refs = (collection: Collection) => (): Option[] =>
  app.objects(collection).map((o) => ({ value: o.id, label: `${o.id} ${o.title}` }))
const values = (...items: string[]) => (): Option[] => items.map((v) => ({ value: v, label: v }))
const zones = (): Option[] =>
  (app.model?.meta.zones ?? []).map((z) => ({ value: z.id, label: `${z.id} ${z.title}` }))
const configurations = (): Option[] =>
  (app.model?.meta.configurations ?? []).map((c) => ({ value: c.id, label: `${c.id} ${c.title}` }))
const assetClasses = (): Option[] =>
  Object.keys(app.method?.asset_classes ?? {}).map((v) => ({ value: v, label: assetClassLabel(app.lang, v) }))
// letter plus name: a lone "I" checkbox says nothing to a newcomer
const stride = (): Option[] => STRIDE.map((s) => ({ value: s, label: `${s} – ${label(app.lang, s)}` }))
const cra = (): Option[] =>
  Object.entries(app.cra).map(([id, e]) => ({ value: id, label: `${id} ${e[app.lang] ?? ''}` }))
const targets = (): Option[] => [...refs('elements')(), ...refs('flows')()]

export const FIELDS: Record<Collection, Field[]> = {
  elements: [
    { key: 'title', label: 'title', type: 'text', required: true },
    { key: 'kind', label: 'kind', type: 'select', options: values('device', 'process', 'datastore', 'external'), required: true },
    { key: 'zone', label: 'zone', type: 'select', options: zones },
    { key: 'configurations', label: 'configurations', type: 'multi', options: configurations },
    { key: 'short_name', label: 'short_name', type: 'text' },
    { key: 'description', label: 'description', type: 'longtext' },
  ],
  flows: [
    { key: 'title', label: 'title', type: 'text', required: true },
    { key: 'source', label: 'source', type: 'select', options: refs('elements'), required: true },
    { key: 'target', label: 'target', type: 'select', options: refs('elements'), required: true },
    { key: 'protocol', label: 'protocol', type: 'text' },
    { key: 'bidirectional', label: 'bidirectional', type: 'bool' },
    { key: 'assets', label: 'assets', type: 'multi', options: refs('assets') },
    { key: 'configurations', label: 'configurations', type: 'multi', options: configurations },
    { key: 'description', label: 'description', type: 'longtext' },
  ],
  assets: [
    { key: 'title', label: 'title', type: 'text', required: true },
    { key: 'asset_class', label: 'asset_class', type: 'select', options: assetClasses, required: true },
    { key: 'protects', label: 'protects', type: 'multi', options: refs('assets') },
    { key: 'amplifier.c', label: 'amplifier', type: 'number' },
    { key: 'amplifier.i', label: 'amplifier', type: 'number' },
    { key: 'amplifier.a', label: 'amplifier', type: 'number' },
    { key: 'amplifier.rationale', label: 'rationale', type: 'longtext' },
    { key: 'description', label: 'description', type: 'longtext' },
  ],
  threats: [
    { key: 'title', label: 'title', type: 'text', required: true },
    { key: 'cyber_cause', label: 'cyber_cause', type: 'tristate' },
    { key: 'stride', label: 'stride', type: 'multi', options: stride },
    { key: 'targets', label: 'targets', type: 'multi', options: targets },
    { key: 'assets', label: 'assets', type: 'multi', options: refs('assets') },
    { key: 'scenario', label: 'scenario', type: 'longtext' },
    { key: 'consequence', label: 'consequence', type: 'longtext' },
    { key: 'safety_related', label: 'safety_related', type: 'bool' },
    { key: 'finding', label: 'finding', type: 'bool' },
    { key: 'configurations', label: 'configurations', type: 'multi', options: configurations },
    { key: 'measures', label: 'measures', type: 'multi', options: refs('measures') },
    { key: 'questions', label: 'questions', type: 'multi', options: refs('questions') },
    { key: 'cra_refs', label: 'cra_refs', type: 'multi', options: cra },
    { key: 'status', label: 'status', type: 'select', options: values('identified', 'assessed', 'treated', 'accepted', 'rejected'), required: true },
    { key: 'acceptance.by', label: 'acceptance_by', type: 'text' },
    { key: 'acceptance.rationale', label: 'acceptance_rationale', type: 'longtext' },
    { key: 'rejection.rationale', label: 'rejection_rationale', type: 'longtext' },
  ],
  measures: [
    { key: 'title', label: 'title', type: 'text', required: true },
    { key: 'kind', label: 'kind', type: 'select', options: values('technical', 'organizational', 'design', 'user_information', 'supply_chain') },
    { key: 'status', label: 'status', type: 'select', options: values('proposed', 'decided', 'in_progress', 'implemented'), required: true },
    { key: 'compensating', label: 'compensating', type: 'bool' },
    { key: 'owner', label: 'owner', type: 'text' },
    { key: 'due', label: 'due', type: 'date' },
    { key: 'evidence', label: 'evidence', type: 'longtext' },
    { key: 'cra_refs', label: 'cra_refs', type: 'multi', options: cra },
    { key: 'description', label: 'description', type: 'longtext' },
  ],
  questions: [
    { key: 'title', label: 'title', type: 'text', required: true },
    { key: 'addressee', label: 'addressee', type: 'text' },
    { key: 'status', label: 'status', type: 'select', options: values('open', 'answered'), required: true },
    { key: 'threats', label: 'threats', type: 'multi', options: refs('threats') },
    { key: 'answer', label: 'answer', type: 'longtext' },
  ],
}

export const NEW: Record<Collection, () => Partial<Obj>> = {
  elements: () => ({ title: '', kind: 'device' }),
  flows: () => ({ title: '', source: '', target: '' }),
  assets: () => ({ title: '', asset_class: '' }),
  threats: () => ({ title: '', stride: [], status: 'identified', assessment: {} }),
  measures: () => ({ title: '', status: 'proposed' }),
  questions: () => ({ title: '', status: 'open' }),
}

// Columns shown in the list next to id and title.
export const COLUMNS: Record<Collection, string[]> = {
  elements: ['kind', 'zone'],
  flows: ['source', 'target', 'protocol'],
  assets: ['asset_class'],
  threats: ['stride', 'status'],
  measures: ['kind', 'status'],
  questions: ['addressee', 'status'],
}

export function getPath(obj: Record<string, any>, path: string): any {
  return path.split('.').reduce<any>((o, k) => (o == null ? undefined : o[k]), obj)
}

/** Set a dotted path; empty values remove the key so defaults stay out of the files. */
export function setPath(obj: Record<string, any>, path: string, value: any): void {
  const parts = path.split('.')
  let node = obj
  for (const part of parts.slice(0, -1)) {
    if (node[part] == null || typeof node[part] !== 'object') node[part] = {}
    node = node[part]
  }
  const last = parts[parts.length - 1]
  if (value === '' || value === undefined) delete node[last]
  else node[last] = value
}

/** Drop empty nested objects (e.g. acceptance without content) before sending. */
export function clean(obj: Record<string, any>): Record<string, any> {
  const out: Record<string, any> = {}
  for (const [k, v] of Object.entries(obj)) {
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      const inner = clean(v)
      if (Object.keys(inner).length > 0 || k === 'assessment') out[k] = inner
    } else if (v !== undefined) {
      out[k] = v
    }
  }
  return out
}
