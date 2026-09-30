import { describe, expect, it } from 'vitest'
import { NAME_LIMIT, normalizeName, validateName } from './name'

describe('normalizeName', () => {
  it('trims the edges and folds inner whitespace into one space', () => {
    expect(normalizeName('  ул.   Ленина,\n 5 ')).toBe('ул. Ленина, 5')
  })
})

describe('validateName', () => {
  it.each(['🚰 Сантехника', 'ул. Ленина, 12А', 'пр-т Мира, 28 к2', '№5 «Наш дом»'])(
    'accepts %s',
    (name) => {
      expect(validateName(name)).toBeNull()
    },
  )

  it('asks for a name', () => {
    expect(validateName('')).toBe('Введите название')
    expect(validateName('  \n ')).toBe('Введите название')
  })

  it('allows exactly the limit and no more', () => {
    expect(validateName('а'.repeat(NAME_LIMIT))).toBeNull()
    expect(validateName('а'.repeat(NAME_LIMIT + 1))).toBe(`Не длиннее ${NAME_LIMIT} символов`)
  })

  it('counts an emoji as one character, as the server does', () => {
    expect(validateName('🚰'.repeat(NAME_LIMIT))).toBeNull()
    expect(validateName('🚰'.repeat(NAME_LIMIT + 1))).not.toBeNull()
  })

  it('measures the name after the spaces are folded', () => {
    expect(validateName(`${'а'.repeat(NAME_LIMIT)}   `)).toBeNull()
  })

  it.each(['*', '_', '~', '^', '+', '`', '[', ']', '#', '>'])(
    'rejects the Max markup character %s',
    (mark) => {
      expect(validateName(`Дом ${mark} 5`)).toBe('Без символов разметки: * _ ~ ^ + ` [ ] # >')
    },
  )
})
