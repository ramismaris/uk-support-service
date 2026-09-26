import { describe, expect, it } from 'vitest'
import { brandInitials } from './brand'

describe('brandInitials', () => {
  it.each([
    ['УК «Наш дом»', 'УН'],
    ['Панель УК', 'ПУ'],
    ['Жилсервис', 'Ж'],
    ['  «»  ', ''],
  ])('%j → %j', (name, initials) => {
    expect(brandInitials(name)).toBe(initials)
  })
})
