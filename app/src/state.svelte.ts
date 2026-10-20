import { api } from './api'
import type { Collection, I18n, Issue, Lang, Method, ModelPayload, Obj, ProjectInfo } from './types'

export type View =
  | { kind: 'start' }
  | { kind: 'overview' }
  | { kind: 'setup'; step: number }
  | { kind: 'validation' }
  | { kind: 'diagram' }
  | { kind: 'assistant'; target: string | null }
  | { kind: 'coverage' }
  | { kind: 'settings' }
  | { kind: 'controls' }
  | { kind: 'documents' }
  | { kind: 'objects'; collection: Collection; selected: string | null }
  | { kind: 'history' }

export interface HistoryEntry {
  id: string
  time: string
  kind: 'auto' | 'save' | 'open'
  counts: Record<Collection, number>
}

const LANG_KEY = 'tw-lang'

/** UI language: the viewer's own pick, else the browser's first language; German only for German. */
function initialLang(): Lang {
  try {
    const stored = localStorage.getItem(LANG_KEY)
    if (stored === 'de' || stored === 'en') return stored
  } catch {
    /* storage unavailable */
  }
  const first = navigator.languages?.[0] ?? navigator.language ?? ''
  return first.toLowerCase().startsWith('de') ? 'de' : 'en'
}

class AppState {
  lang = $state<Lang>(initialLang())

  /** Toggle by the viewer; remembered per browser. The project language only drives documents. */
  setLang(lang: Lang): void {
    this.lang = lang
    try {
      localStorage.setItem(LANG_KEY, lang)
    } catch {
      /* storage unavailable */
    }
  }
  version = $state('')
  recent = $state<string[]>([])
  server = $state(false) // runs as a shared server: workspace and upload instead of local folders
  project = $state<ProjectInfo | null>(null)
  method = $state<Method | null>(null)
  cra = $state<Record<string, I18n>>({})
  modelName = $state<string | null>(null)
  model = $state<ModelPayload | null>(null)
  issues = $state<Issue[]>([])
  view = $state<View>({ kind: 'start' })
  message = $state('')
  externalChange = $state(false)
  cyberCheck = $state<string | null>(null) // threat id awaiting rule 3.3 answer
  changedSince = $state('') // '' = last commit, else a tag/revision
  changed = $state<Set<string>>(new Set())
  tags = $state<{ name: string; date: string }[]>([])
  vcs = $state(false)
  lastAutosave = $state<string | null>(null) // ISO time of the latest autosave in this session
  recovery = $state<HistoryEntry | null>(null) // unsaved autosave found when the project was opened

  /** Snapshot unsaved edits into the version history (never into the project files). */
  async autosave(): Promise<void> {
    if (!this.project?.dirty) return
    const r = await api<{ saved: boolean; time: string | null }>('POST', '/autosave')
    if (r.saved) this.lastAutosave = r.time
  }

  async history(): Promise<{ entries: HistoryEntry[]; pending: string | null }> {
    return api('GET', '/history')
  }

  async restoreVersion(id: string): Promise<void> {
    this.project = await api<ProjectInfo>('POST', `/history/${encodeURIComponent(id)}/restore`)
    this.recovery = null
    await this.refreshModel()
    this.flash('restored')
  }

  async dismissRecovery(): Promise<void> {
    await api('POST', '/history/dismiss')
    this.recovery = null
  }

  async init(): Promise<void> {
    // Loading takes a moment; if the user navigated meanwhile (e.g. created a new project
    // from the start page), their view wins over the landing view. Taken before the first
    // request, so a click during /app counts as navigation too.
    const before = this.view
    const info = await api<{ version: string; recent: string[]; server: boolean }>('GET', '/app')
    this.version = info.version
    this.recent = info.recent
    this.server = info.server
    try {
      await this.loadProject(await api<ProjectInfo>('GET', '/project'))
      // on a server the start page with the project overview comes first
      if (this.view === before) this.view = this.server ? { kind: 'start' } : this.home()
    } catch {
      if (this.view === before) this.view = { kind: 'start' }
    }
  }

  async loadProject(info: ProjectInfo): Promise<void> {
    this.project = info
    this.lastAutosave = null // at the start: a slow load must not hide an autosave made meanwhile
    this.method = await api<Method>('GET', '/method').catch(() => null)
    const cra = await api<{ entries: Record<string, I18n> }>('GET', '/catalog/cra')
    this.cra = cra.entries
    const names = Object.keys(info.models)
    if (!this.modelName || !names.includes(this.modelName)) this.modelName = names[0] ?? null
    await this.refreshModel()
    await this.refreshProject() // `info` may be outdated by now (edits while loading)
    const h = await this.history().catch(() => null)
    this.recovery = h?.entries.find((e) => e.id === h.pending) ?? null
  }

  /** Landing view: the diagram once there is something to see, else the setup wizard. */
  home(): View {
    return this.model && this.objects('elements').length ? { kind: 'diagram' } : { kind: 'setup', step: 0 }
  }

  async refreshProject(): Promise<void> {
    this.project = await api<ProjectInfo>('GET', '/project')
  }

  async refreshModel(): Promise<void> {
    this.model = this.modelName
      ? await api<ModelPayload>('GET', `/models/${this.modelName}`)
      : null
    this.issues = await api<Issue[]>('GET', '/validate')
    await this.refreshChanges()
  }

  async refreshChanges(): Promise<void> {
    const r = await api<{ available: boolean; models: Record<string, string[]>; tags: { name: string; date: string }[] }>(
      'GET',
      `/vcs/changed?since=${encodeURIComponent(this.changedSince)}`,
    )
    this.vcs = r.available
    this.tags = r.tags
    this.changed = new Set(this.modelName ? (r.models[this.modelName] ?? []) : [])
  }

  async afterChange(model?: ModelPayload): Promise<void> {
    if (model) this.model = model
    await this.refreshProject()
    this.issues = await api<Issue[]>('GET', '/validate')
  }

  async save(): Promise<void> {
    if (!this.project) return
    await api('POST', '/save')
    this.externalChange = false
    await this.refreshProject()
    await this.refreshChanges()
    this.flash('saved')
  }

  async undoRedo(which: 'undo' | 'redo'): Promise<void> {
    await api('POST', `/${which}`)
    await this.refreshModel()
    await this.refreshProject()
  }

  async reload(): Promise<void> {
    await this.loadProject(await api<ProjectInfo>('POST', '/reload'))
    this.externalChange = false
  }

  async pollChanges(): Promise<void> {
    if (!this.project) return
    const r = await api<{ changed: string[]; dirty: boolean }>('GET', '/changes')
    if (r.changed.length === 0) return
    if (r.dirty) {
      this.externalChange = true
    } else {
      await this.reload()
      this.flash('reloaded')
    }
  }

  objects(collection: Collection): Obj[] {
    return this.model?.objects[collection] ?? []
  }

  flash(key: string): void {
    this.message = key
    setTimeout(() => {
      if (this.message === key) this.message = ''
    }, 2500)
  }
}

export const app = new AppState()
