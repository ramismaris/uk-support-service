import { describe, expect, it } from 'vitest'
import { insertLink, toggleMarker } from './format-edit'

describe('toggleMarker', () => {
  it('wraps the selection and keeps it selected', () => {
    expect(toggleMarker('Вход с улицы', 0, 4, '**')).toEqual({
      value: '**Вход** с улицы',
      start: 2,
      end: 6,
    })
  })

  it('unwraps a selection that is already wrapped', () => {
    expect(toggleMarker('**Вход** с улицы', 2, 6, '**')).toEqual({
      value: 'Вход с улицы',
      start: 0,
      end: 4,
    })
  })

  it('unwraps when the markers are selected too', () => {
    expect(toggleMarker('**Вход** с улицы', 0, 8, '**')).toEqual({
      value: 'Вход с улицы',
      start: 0,
      end: 4,
    })
  })

  it('puts the cursor between new markers when nothing is selected', () => {
    expect(toggleMarker('Текст ', 6, 6, '_')).toEqual({ value: 'Текст __', start: 7, end: 7 })
  })

  it('keeps spaces around the selection outside the markers', () => {
    expect(toggleMarker('a word b', 1, 7, '~~')).toEqual({
      value: 'a ~~word~~ b',
      start: 4,
      end: 8,
    })
  })
})

describe('insertLink', () => {
  it('turns the selection into link text and selects the address, ready for a paste', () => {
    expect(insertLink('Сайт УК', 0, 4)).toEqual({
      value: '[Сайт](https://) УК',
      start: 7,
      end: 15,
    })
  })

  it('offers a placeholder text when nothing is selected', () => {
    expect(insertLink('', 0, 0)).toEqual({ value: '[ссылка](https://)', start: 9, end: 17 })
  })
})
