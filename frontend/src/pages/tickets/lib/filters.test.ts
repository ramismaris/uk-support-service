import { describe, expect, it } from 'vitest'
import { parseTicketFilters, ticketFiltersToSearch } from './filters'

const defaults = { status: null, mine: false, buildingId: null, categoryId: null }

describe('parseTicketFilters', () => {
  it('reads status and mine', () => {
    expect(parseTicketFilters(new URLSearchParams('status=NEW&mine=1'))).toEqual({
      ...defaults,
      status: 'NEW',
      mine: true,
    })
  })

  it('defaults to all active tickets', () => {
    expect(parseTicketFilters(new URLSearchParams(''))).toEqual(defaults)
  })

  it.each(['CLOSED', 'REJECTED'] as const)('reads the archive status %s', (status) => {
    expect(parseTicketFilters(new URLSearchParams(`status=${status}`))).toEqual({
      ...defaults,
      status,
    })
  })

  it('drops values the list cannot filter by', () => {
    expect(parseTicketFilters(new URLSearchParams('status=ARCHIVED&mine=yes'))).toEqual(defaults)
  })

  it('reads the building and the category', () => {
    expect(parseTicketFilters(new URLSearchParams('building=5&category=12'))).toEqual({
      ...defaults,
      buildingId: 5,
      categoryId: 12,
    })
  })

  it.each(['0', '-3', '1.5', 'abc', '', '7x', '99999999999999999999'])(
    'drops the id %j that is not a positive whole number',
    (value) => {
      expect(parseTicketFilters(new URLSearchParams({ building: value, category: value }))).toEqual(
        defaults,
      )
    },
  )
})

describe('ticketFiltersToSearch', () => {
  it('writes only non-default values', () => {
    expect(
      ticketFiltersToSearch({ ...defaults, status: 'WAITING_CLIENT', mine: true }).toString(),
    ).toBe('status=WAITING_CLIENT&mine=1')
    expect(ticketFiltersToSearch(defaults).toString()).toBe('')
  })

  it('writes the building and the category', () => {
    expect(ticketFiltersToSearch({ ...defaults, buildingId: 5, categoryId: 12 }).toString()).toBe(
      'building=5&category=12',
    )
  })

  it.each(['NEW', 'IN_PROGRESS', 'WAITING_CLIENT', 'CLOSED', 'REJECTED'] as const)(
    'round-trips %s',
    (status) => {
      const filters = { ...defaults, status }
      expect(parseTicketFilters(ticketFiltersToSearch(filters))).toEqual(filters)
    },
  )

  it('round-trips everything at once', () => {
    const filters = { status: 'CLOSED', mine: true, buildingId: 3, categoryId: 9 } as const
    expect(parseTicketFilters(ticketFiltersToSearch(filters))).toEqual(filters)
  })
})
