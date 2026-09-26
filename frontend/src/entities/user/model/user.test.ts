import { describe, expect, it } from 'vitest'
import { getDisplayName, isAdmin, isClient, isStaff, type User } from './user'

const user = (overrides: Partial<User> = {}): User => ({
  id: 1,
  max_user_id: 1000001,
  first_name: 'Анна',
  last_name: null,
  username: null,
  phone: null,
  role: 'CLIENT',
  ...overrides,
})

describe('roles', () => {
  it('treats managers and admins as staff', () => {
    expect(isStaff(user({ role: 'MANAGER' }))).toBe(true)
    expect(isStaff(user({ role: 'ADMIN' }))).toBe(true)
    expect(isStaff(user({ role: 'CLIENT' }))).toBe(false)
  })

  it('recognises admins and clients', () => {
    expect(isAdmin(user({ role: 'ADMIN' }))).toBe(true)
    expect(isAdmin(user({ role: 'MANAGER' }))).toBe(false)
    expect(isClient(user({ role: 'CLIENT' }))).toBe(true)
    expect(isClient(user({ role: 'MANAGER' }))).toBe(false)
  })
})

describe('getDisplayName', () => {
  it('joins first and last name', () => {
    expect(getDisplayName(user({ last_name: 'Петрова' }))).toBe('Анна Петрова')
  })

  it('uses the first name alone when there is no last name', () => {
    expect(getDisplayName(user())).toBe('Анна')
  })
})
