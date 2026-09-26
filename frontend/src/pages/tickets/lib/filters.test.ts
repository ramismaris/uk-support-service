import { describe, expect, it } from 'vitest'
import { parseTicketFilters, ticketFiltersToSearch } from './filters'

describe('parseTicketFilters', () => {
  it('reads status and mine', () => {
    expect(parseTicketFilters(new URLSearchParams('status=NEW&mine=1'))).toEqual({
      status: 'NEW',
      mine: true,
    })
  })

  it('defaults to all active tickets', () => {
    expect(parseTicketFilters(new URLSearchParams(''))).toEqual({ status: null, mine: false })
  })

  it('drops values the list cannot filter by', () => {
    expect(parseTicketFilters(new URLSearchParams('status=CLOSED&mine=yes'))).toEqual({
      status: null,
      mine: false,
    })
  })
})

describe('ticketFiltersToSearch', () => {
  it('writes only non-default values', () => {
    expect(ticketFiltersToSearch({ status: 'WAITING_CLIENT', mine: true }).toString()).toBe(
      'status=WAITING_CLIENT&mine=1',
    )
    expect(ticketFiltersToSearch({ status: null, mine: false }).toString()).toBe('')
  })

  it('round-trips', () => {
    const filters = { status: 'IN_PROGRESS', mine: false } as const
    expect(parseTicketFilters(ticketFiltersToSearch(filters))).toEqual(filters)
  })
})
