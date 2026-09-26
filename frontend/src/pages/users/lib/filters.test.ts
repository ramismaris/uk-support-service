import { describe, expect, it } from 'vitest'
import { parseUserSearch, userFilterToQuery, userSearchToParams } from './filters'

describe('userFilterToQuery', () => {
  it.each([
    ['all', {}],
    ['staff', { role: ['MANAGER', 'ADMIN'] }],
    ['residents', { role: ['CLIENT'] }],
    ['blocked', { is_blocked: true }],
  ] as const)('%s', (filter, query) => {
    expect(userFilterToQuery(filter, '')).toEqual(query)
  })

  it('passes a trimmed search and drops an empty one', () => {
    expect(userFilterToQuery('all', '  Мария ')).toEqual({ q: 'Мария' })
    expect(userFilterToQuery('all', '   ')).toEqual({})
  })
})

describe('parseUserSearch', () => {
  it('reads the filter and the search', () => {
    expect(parseUserSearch(new URLSearchParams('filter=staff&q=Игорь'))).toEqual({
      filter: 'staff',
      q: 'Игорь',
    })
  })

  it('falls back to all for unknown filters', () => {
    expect(parseUserSearch(new URLSearchParams('filter=admins'))).toEqual({ filter: 'all', q: '' })
  })

  it('round-trips through URL params', () => {
    const state = { filter: 'blocked', q: 'Ива' } as const
    expect(parseUserSearch(userSearchToParams(state))).toEqual(state)
    expect(userSearchToParams({ filter: 'all', q: '' }).toString()).toBe('')
  })
})
