import { vi } from 'vitest'

type StubbedResponse = { status: number; body?: unknown }
type Handler = (requestBody: unknown) => StubbedResponse

/**
 * Replaces fetch with a tiny router keyed by "METHOD /path".
 *
 * Stubbing at the network boundary rather than mocking the api module means
 * the tests also cover the request building and error parsing in lib/api.ts.
 */
export function stubBackend(routes: Record<string, Handler>) {
  const fetchStub = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString()
    const route = `${init?.method ?? 'GET'} ${new URL(url).pathname}`
    const handler = routes[route]

    if (handler === undefined) {
      throw new Error(`Unexpected request in test: ${route}`)
    }

    const requestBody = typeof init?.body === 'string' ? JSON.parse(init.body) : undefined
    const { status, body } = handler(requestBody)

    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  })

  vi.stubGlobal('fetch', fetchStub)

  return fetchStub
}
