import { describe, expect, it } from 'vitest'
import { toRequest, validateBroadcast } from './validate'

const draft = (changes: Partial<Parameters<typeof validateBroadcast>[0]> = {}) => ({
  text: 'Отключение воды 12 октября',
  scope: 'all' as const,
  buildingIds: [] as number[],
  ...changes,
})

describe('validateBroadcast', () => {
  it('accepts a text for everyone', () => {
    expect(validateBroadcast(draft())).toEqual({})
  })

  it('asks for a text', () => {
    expect(validateBroadcast(draft({ text: '   ' })).text).toBe('Заполните текст')
  })

  it('stops a text over the limit', () => {
    expect(validateBroadcast(draft({ text: 'а'.repeat(3001) })).text).toBe(
      'Не длиннее 3000 символов',
    )
    expect(validateBroadcast(draft({ text: 'а'.repeat(3000) })).text).toBeUndefined()
  })

  it('needs a building when the buildings are chosen one by one', () => {
    expect(validateBroadcast(draft({ scope: 'selected' })).buildings).toBe(
      'Выберите хотя бы один дом',
    )
    expect(validateBroadcast(draft({ scope: 'selected', buildingIds: [4] }))).toEqual({})
  })

  it('does not look at the chosen buildings when the message goes to everyone', () => {
    expect(validateBroadcast(draft({ buildingIds: [] })).buildings).toBeUndefined()
  })

  it('allows at most 100 buildings', () => {
    const many = Array.from({ length: 101 }, (_, index) => index + 1)
    expect(validateBroadcast(draft({ scope: 'selected', buildingIds: many })).buildings).toBe(
      'Не больше 100 домов',
    )
  })
})

describe('toRequest', () => {
  it('sends no buildings for everyone, even with a leftover selection', () => {
    expect(toRequest(draft({ buildingIds: [1, 2] }), null)).toEqual({
      text: 'Отключение воды 12 октября',
      file_id: null,
      building_ids: null,
    })
  })

  it('sends the chosen buildings and the photo', () => {
    expect(toRequest(draft({ scope: 'selected', buildingIds: [3, 4] }), 12)).toEqual({
      text: 'Отключение воды 12 октября',
      file_id: 12,
      building_ids: [3, 4],
    })
  })
})
