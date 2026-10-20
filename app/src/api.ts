// Thin client for the local server. Every request carries X-Threatwright: other
// websites cannot add that header without a CORS preflight, which the server never
// grants, so they cannot send requests on the user's behalf (CSRF). The login, if
// any, is HTTP Basic Auth handled by the browser.

const HEADER = { 'X-Threatwright': '1' }

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
    headers: { ...HEADER, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, data.detail)
  }
  return response.json() as Promise<T>
}

/** Send a file as raw request body (e.g. a zipped project or an OSCAL JSON file). */
export async function upload<T>(path: string, file: Blob): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { ...HEADER, 'Content-Type': file.type || 'application/octet-stream' },
    body: file,
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, data.detail)
  }
  return response.json() as Promise<T>
}

/** Download an API resource (e.g. the diagram SVG) as a file. */
export async function download(path: string, filename: string): Promise<void> {
  const response = await fetch(`/api${path}`, { headers: HEADER })
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, data.detail)
  }
  const url = URL.createObjectURL(await response.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
