import { describe, expect, it } from 'vitest'
import type { User } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { resolveSessionState, type SessionInput } from './session-state'

const user: User = {
  id: 1,
  max_user_id: 1000002,
  first_name: 'Игорь',
  last_name: null,
  username: null,
  phone: null,
  role: 'MANAGER',
}

const input = (overrides: Partial<SessionInput> = {}): SessionInput => ({
  token: null,
  inMax: false,
  me: { data: undefined, error: null },
  maxLogin: { error: null },
  ...overrides,
})

describe('resolveSessionState with a token', () => {
  it('is ready when /me returned the user', () => {
    expect(resolveSessionState(input({ token: 't', me: { data: user, error: null } }))).toEqual({
      kind: 'ready',
      user,
    })
  })

  it('is loading while /me is in flight', () => {
    expect(resolveSessionState(input({ token: 't' }))).toEqual({ kind: 'loading' })
  })

  it('stays loading on 401 until the unauthorized handler drops the token', () => {
    const me = { data: undefined, error: new ApiError(401, 'Токен истёк') }
    expect(resolveSessionState(input({ token: 't', me }))).toEqual({ kind: 'loading' })
  })

  it('is blocked on 403', () => {
    const me = { data: undefined, error: new ApiError(403, 'Пользователь заблокирован') }
    expect(resolveSessionState(input({ token: 't', me }))).toEqual({
      kind: 'blocked',
      canSignOut: true,
    })
  })

  it('shows an error on a server failure and keeps the token', () => {
    const me = { data: undefined, error: new ApiError(500, 'Ошибка сервера') }
    expect(resolveSessionState(input({ token: 't', me }))).toEqual({
      kind: 'error',
      message: 'Ошибка сервера',
      canSignOut: true,
    })
  })

  it('shows a connection error when the network fails', () => {
    const me = { data: undefined, error: new TypeError('Failed to fetch') }
    expect(resolveSessionState(input({ token: 't', me }))).toEqual({
      kind: 'error',
      message: 'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.',
      canSignOut: true,
    })
  })
})

describe('sign-out from dead-end screens', () => {
  const blockedMe = { data: undefined, error: new ApiError(403, 'Пользователь заблокирован') }
  const failedMe = { data: undefined, error: new ApiError(500, 'Ошибка сервера') }

  it('offers sign-out in the browser when blocked or failing', () => {
    expect(resolveSessionState(input({ token: 't', me: blockedMe }))).toMatchObject({
      canSignOut: true,
    })
    expect(resolveSessionState(input({ token: 't', me: failedMe }))).toMatchObject({
      canSignOut: true,
    })
  })

  it('does not offer sign-out inside Max, where sign-in is automatic', () => {
    expect(resolveSessionState(input({ inMax: true, token: 't', me: blockedMe }))).toMatchObject({
      canSignOut: false,
    })
    expect(resolveSessionState(input({ inMax: true, token: 't', me: failedMe }))).toMatchObject({
      canSignOut: false,
    })
  })
})

describe('resolveSessionState without a token', () => {
  it('sends a browser user to the login page', () => {
    expect(resolveSessionState(input())).toEqual({ kind: 'unauthenticated' })
  })

  it('sends a browser user to login even if stale /me data is cached', () => {
    expect(resolveSessionState(input({ me: { data: user, error: null } }))).toEqual({
      kind: 'unauthenticated',
    })
  })

  it('is loading inside Max while signing in with initData', () => {
    expect(resolveSessionState(input({ inMax: true }))).toEqual({ kind: 'loading' })
  })

  it('is blocked when Max sign-in returns 403', () => {
    const maxLogin = { error: new ApiError(403, 'Пользователь заблокирован') }
    expect(resolveSessionState(input({ inMax: true, maxLogin }))).toEqual({
      kind: 'blocked',
      canSignOut: false,
    })
  })

  it('shows an error when initData is rejected', () => {
    const maxLogin = { error: new ApiError(401, 'Неверная подпись') }
    expect(resolveSessionState(input({ inMax: true, maxLogin }))).toEqual({
      kind: 'error',
      message: 'Неверная подпись',
      canSignOut: false,
    })
  })
})
