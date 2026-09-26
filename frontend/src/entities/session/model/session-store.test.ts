import { beforeEach, describe, expect, it } from 'vitest'
import { useSessionStore } from './session-store'

beforeEach(() => {
  useSessionStore.getState().clear()
  localStorage.clear()
})

describe('session store', () => {
  it('stores the token and persists it', () => {
    useSessionStore.getState().setToken('abc')
    expect(useSessionStore.getState().token).toBe('abc')
    expect(JSON.parse(localStorage.getItem('uk-session')!).state).toEqual({ token: 'abc' })
  })

  it('clears the token', () => {
    useSessionStore.getState().setToken('abc')
    useSessionStore.getState().clear()
    expect(useSessionStore.getState().token).toBeNull()
  })
})
