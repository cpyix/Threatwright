// Thin client for the local server. The session token arrives in the URL
// fragment (never sent to the server in URLs or logs) and is kept per tab.

function readToken(): string {
  const match = location.hash.match(/token=([^&]+)/)
  try {
    if (match) {
      sessionStorage.setItem('tw-token', match[1])
      history.replaceState(null, '', location.pathname)
      return match[1]
    }
    return sessionStorage.getItem('tw-token') ?? ''
  } catch {
    return match ? match[1] : ''
  }
}

const token = readToken()

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(formatDetail(detail))
  }
}

function formatDetail(detail: unknown): string {
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).join('.')}: ${d.msg ?? ''}`)
      .join('\n')
  }
  return typeof detail === 'string' ? detail : JSON.stringify(detail)
}

export async function api<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: { 'X-Threatwright-Token': token, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, data.detail)
  }
  return response.json() as Promise<T>
}

/** Download an API resource (e.g. the diagram SVG) as a file. */
export async function download(path: string, filename: string): Promise<void> {
  const response = await fetch(`/api${path}`, { headers: { 'X-Threatwright-Token': token } })
  if (!response.ok) throw new ApiError(response.status, response.statusText)
  const url = URL.createObjectURL(await response.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
