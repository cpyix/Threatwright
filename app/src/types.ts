export type Lang = 'de' | 'en'
export type I18n = { de: string; en: string }
export type Obj = Record<string, any> & { id: string; title: string }

export const COLLECTIONS = ['elements', 'flows', 'assets', 'threats', 'measures', 'questions'] as const
export type Collection = (typeof COLLECTIONS)[number]

export interface ProjectInfo {
  root: string
  config: { name: string; language: Lang; method: string; libraries: string[]; lifecycle: string }
  custom_fields: { fields: Record<string, CustomField[]> }
  models: Record<string, { title: string; counts: Record<Collection, number> }>
  product_libraries: string[]
  dirty: boolean
  can_undo: boolean
  can_redo: boolean
}

export interface CustomField {
  name: string
  label: Partial<I18n>
  type: string
  required: boolean
  options: string[]
  help: Partial<I18n>
}

export interface Evaluation {
  exposure: number | null
  impact: number | null
  risk: number | null
  max_acceptable_risk: number
  acceptable: boolean | null
  rules: string[]
}

export interface ThreatEvaluation {
  assessment: Evaluation
  residual: Evaluation | null
  suggestion: { impact: number; asset_id: string; dimension: string } | null
}

export interface Note {
  x: number
  y: number
  text: string
}

export interface ModelPayload {
  name: string
  meta: {
    title: string
    description: string | null
    zones: { id: string; title: string; environment: Record<string, string | null> }[]
    configurations: { id: string; title: string }[]
  }
  objects: Record<Collection, Obj[]>
  evaluations: Record<string, ThreatEvaluation>
  max_risks: Record<string, number>
  layout: { nodes: Record<string, { x: number; y: number }>; notes: Record<string, Note> }
  asset_impacts: Record<string, Record<'C' | 'I' | 'A', number | null>>
}

export interface IndicatorValue extends I18n {
  factor: string
  help?: Partial<I18n>
}

export interface Method {
  id: string
  title: I18n
  impact_levels: { levels: Record<string, I18n> }
  risk_levels: { levels: Record<string, I18n> }
  asset_classes: Record<string, { source: string }>
  interface: { source: string; values: Record<string, IndicatorValue> }
  access: { source: string; values: Record<string, IndicatorValue> }
  user: { source: string; values: Record<string, IndicatorValue> }
  risk_matrix: { matrix_row_from_exposure: 'literal' | 'inverted' }
  acceptance: { max_acceptable_risk: number }
  stride_per_kind: { map: Record<string, string[]> }
}

export interface ElementType {
  id: string
  name: I18n
  kind: 'process' | 'device' | 'datastore' | 'external' | 'flow'
  icon: string | null
  category: string | null
  description: I18n | null
  environment: { interface: string | null; access: string | null; user: string | null }
  assets: { title: I18n; asset_class: string }[]
}

export interface Suggestion {
  template_id: string
  title: string
  scenario: string
  impact: number | null
  safety_related: boolean
  adopted: boolean
}

export interface Category {
  relevant: boolean
  existing: string[]
  not_relevant: string | null
  suggestions: Suggestion[]
}

export interface CoverageRow {
  id: string
  title: string
  kind: string
  cells: Record<string, Category>
}

export interface Issue {
  severity: 'error' | 'warning'
  code: string
  file: string
  model: string | null
  object: string | null
  location: string
  message: string
}
