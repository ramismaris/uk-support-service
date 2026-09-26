import type { User } from '@/entities/user'
import { isApiError } from '@/shared/api'

export type SessionState =
  | { kind: 'loading' }
  | { kind: 'ready'; user: User }
  | { kind: 'unauthenticated' }
  | { kind: 'blocked' }
  | { kind: 'error'; message: string }

export interface SessionInput {
  token: string | null
  inMax: boolean
  me: { data: User | undefined; error: unknown }
  maxLogin: { error: unknown }
}

const NETWORK_ERROR = 'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.'

function errorMessage(error: unknown): string {
  return isApiError(error) ? error.message : NETWORK_ERROR
}

export function resolveSessionState({ token, inMax, me, maxLogin }: SessionInput): SessionState {
  if (token !== null && me.data) {
    return { kind: 'ready', user: me.data }
  }
  if (isApiError(me.error, 403) || isApiError(maxLogin.error, 403)) {
    return { kind: 'blocked' }
  }
  if (token !== null) {
    // 401 means the token is being dropped by the api client; wait for that.
    if (me.error && !isApiError(me.error, 401)) {
      return { kind: 'error', message: errorMessage(me.error) }
    }
    return { kind: 'loading' }
  }
  if (!inMax) {
    return { kind: 'unauthenticated' }
  }
  if (maxLogin.error) {
    return { kind: 'error', message: errorMessage(maxLogin.error) }
  }
  return { kind: 'loading' }
}
