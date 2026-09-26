import { describe, expect, it } from 'vitest'
import { validateTheme } from './validate'

const draft = (companyName = 'УК «Наш дом»', primaryColor = '#2f6fed') => ({
  companyName,
  primaryColor,
})

describe('validateTheme', () => {
  it('accepts a filled draft', () => {
    expect(validateTheme(draft())).toEqual({})
    expect(validateTheme(draft('У', '#ABCDEF'))).toEqual({})
  })

  it('requires the company name and limits it', () => {
    expect(validateTheme(draft('   '))).toEqual({ companyName: 'Укажите название' })
    expect(validateTheme(draft('а'.repeat(101)))).toEqual({
      companyName: 'Не длиннее 100 символов',
    })
  })

  it('requires a #RRGGBB colour', () => {
    for (const color of ['', '#fff', '2f6fed', '#2f6fez', '#2f6fed0']) {
      expect(validateTheme(draft(undefined, color))).toEqual({
        primaryColor: 'Цвет в формате #RRGGBB',
      })
    }
  })
})
