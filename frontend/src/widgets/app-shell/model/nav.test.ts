import { describe, expect, it } from 'vitest'
import type { User } from '@/entities/user'
import { visibleNavItems } from './nav'

const user = (role: User['role']): User => ({
  id: 1,
  max_user_id: 1,
  first_name: 'Тест',
  last_name: null,
  username: null,
  phone: null,
  role,
})

describe('visibleNavItems', () => {
  it('shows only tickets to a manager', () => {
    expect(visibleNavItems(user('MANAGER')).map((item) => item.key)).toEqual(['tickets'])
  })

  it('hides sections that are not built yet, even from an admin', () => {
    expect(visibleNavItems(user('ADMIN')).map((item) => item.key)).toEqual(['tickets'])
  })
})
