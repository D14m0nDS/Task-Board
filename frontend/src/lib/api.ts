const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  token?: string | null
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, token } = options

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response))
  }

  return (response.status === 204 ? undefined : await response.json()) as T
}

/**
 * FastAPI reports its own errors as a string in `detail`, but validation
 * failures arrive as a list of per-field objects instead.
 */
async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = await response.json()

    if (typeof payload.detail === 'string') {
      return payload.detail
    }

    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item: { msg: string }) => item.msg).join(', ')
    }
  } catch {
    // Body was not JSON; fall back to the status text below.
  }

  return response.statusText || 'Request failed'
}
