import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  applyTheme,
  DEFAULT_THEME,
  LOGO_FRESH_MS,
  paintTheme,
  readCachedTheme,
  themeFromResponse,
} from './theme'

const NOW = 1_000_000

afterEach(() => {
  vi.restoreAllMocks()
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

describe('paintTheme', () => {
  it('sets the brand colour and the tab title, and leaves the cache alone', () => {
    paintTheme({ companyName: 'УК Центр', primaryColor: '#00a36c', logoUrl: '/logo' })
    expect(document.documentElement.style.getPropertyValue('--brand')).toBe('#00a36c')
    expect(document.title).toBe('УК Центр — панель')
    expect(localStorage.getItem('uk-theme')).toBeNull()
  })
})

describe('applyTheme', () => {
  it('paints the theme and caches it with the logo and the time', () => {
    applyTheme({ companyName: 'УК Центр', primaryColor: '#00a36c', logoUrl: '/logo' }, NOW)
    expect(document.documentElement.style.getPropertyValue('--brand')).toBe('#00a36c')
    expect(document.title).toBe('УК Центр — панель')
    expect(JSON.parse(localStorage.getItem('uk-theme')!)).toEqual({
      companyName: 'УК Центр',
      primaryColor: '#00a36c',
      logoUrl: '/logo',
      savedAt: NOW,
    })
  })

  it('caches a theme without a logo', () => {
    applyTheme({ companyName: 'УК Центр', primaryColor: '#00a36c', logoUrl: null }, NOW)
    expect(JSON.parse(localStorage.getItem('uk-theme')!).logoUrl).toBeNull()
  })

  it('still applies the theme when storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError')
    })
    expect(() =>
      applyTheme({ companyName: 'УК Центр', primaryColor: '#00a36c', logoUrl: null }),
    ).not.toThrow()
    expect(document.documentElement.style.getPropertyValue('--brand')).toBe('#00a36c')
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

  it('reads a cache from before the logo was stored, without a logo', () => {
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

  it('gives back the logo while its signed link is still good', () => {
    applyTheme({ companyName: 'УК Центр', primaryColor: '#00a36c', logoUrl: '/logo' }, NOW)
    expect(readCachedTheme(NOW + LOGO_FRESH_MS).logoUrl).toBe('/logo')
  })

  it('drops the logo once its link may have expired, and keeps the name and colour', () => {
    applyTheme({ companyName: 'УК Центр', primaryColor: '#00a36c', logoUrl: '/logo' }, NOW)
    expect(readCachedTheme(NOW + LOGO_FRESH_MS + 1)).toEqual({
      companyName: 'УК Центр',
      primaryColor: '#00a36c',
      logoUrl: null,
    })
  })
})
