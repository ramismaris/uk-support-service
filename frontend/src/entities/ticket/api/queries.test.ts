import { describe, expect, it } from 'vitest'
import type { TicketPage } from '../model/types'
import { nextPageOffset } from './queries'

const page = (count: number, total: number): TicketPage => ({
  total,
  items: Array.from({ length: count }, () => ({}) as TicketPage['items'][number]),
})

describe('nextPageOffset', () => {
  it('asks for the next page while fewer than total are loaded', () => {
    expect(nextPageOffset([page(50, 120)])).toBe(50)
    expect(nextPageOffset([page(50, 120), page(50, 120)])).toBe(100)
  })

  it('stops when everything is loaded', () => {
    expect(nextPageOffset([page(50, 120), page(50, 120), page(20, 120)])).toBeUndefined()
    expect(nextPageOffset([page(0, 0)])).toBeUndefined()
  })
})
