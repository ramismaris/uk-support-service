import { afterEach, describe, expect, it, vi } from 'vitest'
import { authMiddleware, setTokenGetter, setUnauthorizedHandler } from './client'

type OnRequestParams = Parameters<NonNullable<typeof authMiddleware.onRequest>>[0]
type OnResponseParams = Parameters<NonNullable<typeof authMiddleware.onResponse>>[0]

const URL_ME = 'http://localhost/api/v1/me'

async function runOnRequest(request: Request): Promise<Request> {
  return (await authMiddleware.onRequest!({ request } as OnRequestParams)) as Request
}

async function runOnResponse(request: Request, status: number): Promise<void> {
  await authMiddleware.onResponse!({
    request,
    response: new Response(null, { status }),
  } as OnResponseParams)
}

afterEach(() => {
  setTokenGetter(() => null)
  setUnauthorizedHandler(() => {})
})

describe('authMiddleware', () => {
  it('adds a bearer token when there is one', async () => {
    setTokenGetter(() => 'abc')
    const request = await runOnRequest(new Request(URL_ME))
    expect(request.headers.get('Authorization')).toBe('Bearer abc')
  })

  it('sends no Authorization header without a token', async () => {
    const request = await runOnRequest(new Request(URL_ME))
    expect(request.headers.has('Authorization')).toBe(false)
  })

  it('calls the unauthorized handler on 401 for an authenticated request', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    const request = new Request(URL_ME, { headers: { Authorization: 'Bearer stale' } })
    await runOnResponse(request, 401)
    expect(handler).toHaveBeenCalledOnce()
  })

  it('ignores 401 for a request sent without a token', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    await runOnResponse(new Request('http://localhost/api/v1/auth/max'), 401)
    expect(handler).not.toHaveBeenCalled()
  })

  it('ignores 403', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    const request = new Request(URL_ME, { headers: { Authorization: 'Bearer t' } })
    await runOnResponse(request, 403)
    expect(handler).not.toHaveBeenCalled()
  })
})
