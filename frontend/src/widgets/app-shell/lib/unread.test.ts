import { describe, expect, it } from 'vitest'
import { unreadBadge, withUnreadCount } from './unread'

describe('unreadBadge', () => {
  it('shows nothing when everything is read', () => {
    expect(unreadBadge(0)).toBeNull()
  })

  it('shows the count, capped like in messengers', () => {
    expect(unreadBadge(7)).toBe('7')
    expect(unreadBadge(99)).toBe('99')
    expect(unreadBadge(120)).toBe('99+')
  })
})

describe('withUnreadCount', () => {
  it('prefixes the tab title with the count', () => {
    expect(withUnreadCount('УК — панель', 3)).toBe('(3) УК — панель')
  })

  it('replaces an earlier count instead of stacking', () => {
    expect(withUnreadCount('(3) УК — панель', 5)).toBe('(5) УК — панель')
  })

  it('drops the prefix when all is read', () => {
    expect(withUnreadCount('(3) УК — панель', 0)).toBe('УК — панель')
  })
})
