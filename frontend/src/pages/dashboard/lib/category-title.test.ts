import { describe, expect, it } from 'vitest'
import { splitCategoryTitle } from './category-title'

describe('splitCategoryTitle', () => {
  it('splits the leading emoji from the name', () => {
    expect(splitCategoryTitle('🔧 Сантехника')).toEqual({ emoji: '🔧', name: 'Сантехника' })
    expect(splitCategoryTitle('🌳 Благоустройство')).toEqual({
      emoji: '🌳',
      name: 'Благоустройство',
    })
  })

  it('keeps an emoji with a variation selector whole', () => {
    expect(splitCategoryTitle('❓\uFE0F Другое')).toEqual({ emoji: '❓\uFE0F', name: 'Другое' })
  })

  it('has no emoji when the title starts with a letter', () => {
    expect(splitCategoryTitle('Отопление')).toEqual({ emoji: null, name: 'Отопление' })
  })

  it('does not mistake a digit for an emoji', () => {
    expect(splitCategoryTitle('24 часа')).toEqual({ emoji: null, name: '24 часа' })
  })
})
