import { afterEach, describe, expect, it } from 'vitest'
import { applyTheme, DEFAULT_THEME, readCachedTheme, themeFromResponse } from './theme'

afterEach(() => {
  localStorage.clear()
  document.documentElement.style.removeProperty('--brand')
  document.title = ''
})

describe('themeFromResponse', () => {
  it('falls back to the defaults when the theme is not set up (404)', () => {
    expect(themeFromResponse(null)).toEqual(DEFAULT_THEME)
  })

  it('maps the API fields', () => {
    expect(
      themeFromResponse({
        company_name: 'УК Центр',
        primary_color: '#00a36c',
        logo_file_id: 5,
        logo_url: '/api/v1/files/5?sig=x',
      }),
    ).toEqual({
      companyName: 'УК Центр',
      primaryColor: '#00a36c',
      logoUrl: '/api/v1/files/5?sig=x',
    })
  })
})

describe('applyTheme', () => {
  it('sets the brand colour, the tab title and caches the theme without the logo', () => {
    applyTheme({ companyName: 'УК Центр', primaryColor: '#00a36c', logoUrl: '/logo' })
    expect(document.documentElement.style.getPropertyValue('--brand')).toBe('#00a36c')
    expect(document.title).toBe('УК Центр — панель')
    expect(JSON.parse(localStorage.getItem('uk-theme')!)).toEqual({
      companyName: 'УК Центр',
      primaryColor: '#00a36c',
    })
  })
})

describe('readCachedTheme', () => {
  it('returns the defaults without a cache or with a broken one', () => {
    expect(readCachedTheme()).toEqual(DEFAULT_THEME)
    localStorage.setItem('uk-theme', '{oops')
    expect(readCachedTheme()).toEqual(DEFAULT_THEME)
    localStorage.setItem('uk-theme', JSON.stringify({ companyName: 1, primaryColor: 'red' }))
    expect(readCachedTheme()).toEqual(DEFAULT_THEME)
  })

  it('returns the cached name and colour without a logo', () => {
    localStorage.setItem(
      'uk-theme',
      JSON.stringify({ companyName: 'УК Центр', primaryColor: '#00a36c' }),
    )
    expect(readCachedTheme()).toEqual({
      companyName: 'УК Центр',
      primaryColor: '#00a36c',
      logoUrl: null,
    })
  })
})
