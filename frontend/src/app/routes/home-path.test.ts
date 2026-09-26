import { describe, expect, it } from 'vitest'
import type { User } from '@/entities/user'
import { homePathFor } from './home-path'

const user = (role: User['role']): User => ({
  id: 1,
  max_user_id: 1,
  first_name: 'Тест',
  last_name: null,
  username: null,
  phone: null,
  role,
})

describe('homePathFor', () => {
  it.each([
    ['ADMIN', '/staff'],
    ['MANAGER', '/staff'],
    ['CLIENT', '/client'],
  ] as const)('sends %s to %s', (role, path) => {
    expect(homePathFor(user(role))).toBe(path)
  })
})
