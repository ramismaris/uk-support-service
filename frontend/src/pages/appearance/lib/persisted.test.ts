import { describe, expect, it } from 'vitest'
import { restoreTheme, storableTheme } from './persisted'

const saved = { companyName: 'УК «Наш дом»', primaryColor: '#1e88e5', logo: { id: 4, url: 'u' } }

describe('storableTheme', () => {
  it('keeps the name and the colour and leaves the logo out', () => {
    expect(storableTheme(saved)).toEqual({ companyName: 'УК «Наш дом»', primaryColor: '#1e88e5' })
  })
})

describe('restoreTheme', () => {
  it('puts the stored name and colour over the saved theme and keeps the saved logo', () => {
    expect(restoreTheme(saved, { companyName: 'Новое имя', primaryColor: '#ff0000' })).toEqual({
      companyName: 'Новое имя',
      primaryColor: '#ff0000',
      logo: saved.logo,
    })
  })

  it.each([
    ['nothing', null],
    ['a name that is not a string', { companyName: 1, primaryColor: '#fff' }],
    ['no colour', { companyName: 'а' }],
  ])('rejects %s', (_name, stored) => {
    expect(restoreTheme(saved, stored)).toBeNull()
  })
})
