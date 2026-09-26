import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './schema'

let getToken: () => string | null = () => null
let handleUnauthorized: () => void = () => {}

export function setTokenGetter(getter: () => string | null): void {
  getToken = getter
}

export function setUnauthorizedHandler(handler: () => void): void {
  handleUnauthorized = handler
}

export const authMiddleware: Middleware = {
  onRequest({ request }) {
    const token = getToken()
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`)
    }
    return request
  },
  onResponse({ request, response }) {
    // Only a rejected token means the session is gone; login endpoints send no token.
    if (response.status === 401 && request.headers.has('Authorization')) {
      handleUnauthorized()
    }
    return response
  },
}

export const api = createClient<paths>({ baseUrl: window.location.origin })
api.use(authMiddleware)
