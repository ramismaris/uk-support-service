import { describe, expect, it } from 'vitest'
import { systemText } from './system-text'

describe('systemText', () => {
  it.each([
    ['🟢 Статус заявки №1001: В работе.', 'Статус заявки №1001: В работе.'],
    ['🟡 Статус заявки №1001: Нужен ваш ответ.', 'Статус заявки №1001: Нужен ваш ответ.'],
    ['✅️  Готово', 'Готово'],
    ['Без эмодзи', 'Без эмодзи'],
    ['Статус 🟢 в середине', 'Статус 🟢 в середине'],
  ])('strips the leading emoji from %j', (input, output) => {
    expect(systemText(input)).toBe(output)
  })

  it('keeps an empty text empty', () => {
    expect(systemText(null)).toBe('')
  })
})
