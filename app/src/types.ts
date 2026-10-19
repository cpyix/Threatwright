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

export interface ModelPayload {
  name: string
  meta: {
    title: string
    zones: { id: string; title: string; environment: Record<string, string | null> }[]
    configurations: { id: string; title: string }[]
  }
  objects: Record<Collection, Obj[]>
  evaluations: Record<string, ThreatEvaluation>
  asset_impacts: Record<string, Record<'C' | 'I' | 'A', number | null>>
}

export interface IndicatorValue extends I18n {
  factor: string
}

export interface Method {
  id: string
  title: I18n
  impact_levels: { levels: Record<string, I18n> }
  risk_levels: { levels: Record<string, I18n> }
  asset_classes: Record<string, { source: string }>
  interface: { values: Record<string, IndicatorValue> }
  access: { values: Record<string, IndicatorValue> }
  user: { values: Record<string, IndicatorValue> }
  risk_matrix: { matrix_row_from_exposure: 'literal' | 'inverted' }
  acceptance: { max_acceptable_risk: number }
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
