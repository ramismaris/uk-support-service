import { describe, expect, it } from 'vitest'
import { isDirty } from './dirty'

const contacts = {
  text: 'Звоните',
  phones: [
    { title: 'А', phone: '1' },
    { title: 'Б', phone: '2' },
  ],
}

describe('isDirty', () => {
  it('is clean for an equal draft', () => {
    expect(isDirty(contacts, structuredClone(contacts))).toBe(false)
  })

  it('notices a changed text, order of phones and photo', () => {
    expect(isDirty(contacts, { ...contacts, text: 'Пишите' })).toBe(true)
    expect(isDirty(contacts, { ...contacts, phones: [...contacts.phones].reverse() })).toBe(true)
    expect(
      isDirty(
        { text: 'Т', photo: { id: 1, url: '/a' } },
        { text: 'Т', photo: { id: 2, url: '/b' } },
      ),
    ).toBe(true)
  })

  it('ignores a new signed url for the same photo', () => {
    expect(
      isDirty(
        { text: 'Т', photo: { id: 1, url: '/a?sig=1' } },
        { text: 'Т', photo: { id: 1, url: '/a?sig=2' } },
      ),
    ).toBe(false)
  })
})
