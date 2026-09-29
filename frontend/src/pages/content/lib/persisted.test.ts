import { describe, expect, it } from 'vitest'
import { restoreSectionDraft, storableDraft } from './persisted'
import type { Drafts } from './sections'

const photo = { id: 3, url: 'https://files/3' }

describe('storableDraft', () => {
  it('leaves the photo out: its signed link does not last', () => {
    const welcome: Drafts['welcome'] = { text: 'Здравствуйте', photo }
    expect(storableDraft(welcome)).toEqual({ text: 'Здравствуйте' })
  })

  it('keeps every other field', () => {
    const payment: Drafts['payment'] = { text: 'а', url: 'https://pay', buttonText: 'Оплатить' }
    expect(storableDraft(payment)).toEqual(payment)
  })
})

describe('restoreSectionDraft', () => {
  it('puts the stored text over the saved welcome and keeps the saved photo', () => {
    const saved: Drafts['welcome'] = { text: 'Старый', photo }
    expect(restoreSectionDraft('welcome', saved, { text: 'Новый' })).toEqual({
      text: 'Новый',
      photo,
    })
  })

  it('restores the payment fields', () => {
    const saved: Drafts['payment'] = { text: '', url: '', buttonText: '' }
    const stored = { text: 'Оплата', url: 'https://pay', buttonText: 'Оплатить' }
    expect(restoreSectionDraft('payment', saved, stored)).toEqual(stored)
  })

  it('restores the phones', () => {
    const saved: Drafts['contacts'] = { text: '', phones: [] }
    const stored = { text: 'Звоните', phones: [{ title: 'Диспетчер', phone: '112' }] }
    expect(restoreSectionDraft('contacts', saved, stored)).toEqual(stored)
  })

  it.each([
    ['welcome', { text: 5 }],
    ['welcome', null],
    ['payment', { text: 'а', url: 'u' }],
    ['contacts', { text: 'а', phones: [{ title: 'Диспетчер' }] }],
    ['contacts', { text: 'а', phones: 'не список' }],
  ] as const)('rejects a broken %s draft', (section, stored) => {
    const saved: Drafts[typeof section] =
      section === 'welcome'
        ? { text: '', photo: null }
        : section === 'payment'
          ? { text: '', url: '', buttonText: '' }
          : ({ text: '', phones: [] } as never)
    expect(restoreSectionDraft(section, saved as never, stored)).toBeNull()
  })
})
