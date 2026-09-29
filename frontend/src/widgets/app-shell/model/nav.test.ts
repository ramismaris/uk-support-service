import { describe, expect, it } from 'vitest'
import type { User } from '@/entities/user'
import { isNavItemActive, visibleNavItems } from './nav'

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

  it('shows the admin sections to an admin', () => {
    expect(visibleNavItems(user('ADMIN')).map((item) => item.key)).toEqual([
      'dashboard',
      'tickets',
      'content',
      'users',
      'appearance',
    ])
  })
})

describe('isNavItemActive', () => {
  const [dashboard, tickets, content] = visibleNavItems(user('ADMIN'))

  it('keeps tickets active on the list and on a ticket, not on admin sections', () => {
    expect(isNavItemActive(tickets, '/staff')).toBe(true)
    expect(isNavItemActive(tickets, '/staff/tickets/1000')).toBe(true)
    expect(isNavItemActive(tickets, '/staff/content')).toBe(false)
    expect(isNavItemActive(tickets, '/staff/dashboard')).toBe(false)
  })

  it('keeps the dashboard to its own page', () => {
    expect(isNavItemActive(dashboard, '/staff/dashboard')).toBe(true)
    expect(isNavItemActive(dashboard, '/staff')).toBe(false)
  })

  it('matches a section and its sub-pages', () => {
    expect(isNavItemActive(content, '/staff/content')).toBe(true)
    expect(isNavItemActive(content, '/staff/content/payment')).toBe(true)
    expect(isNavItemActive(content, '/staff/contents')).toBe(false)
  })
})
