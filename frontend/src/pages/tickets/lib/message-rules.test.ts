import { describe, expect, it } from 'vitest'
import { hasContent, validateMessage } from './message-rules'

const MB = 1024 * 1024
const photo = (name = 'a.jpg', size = MB) => ({ name, type: 'image/jpeg', size })
const pdf = (name = 'act.pdf', size = MB) => ({ name, type: 'application/pdf', size })

describe('hasContent', () => {
  it('needs text that is not only spaces, or files', () => {
    expect(hasContent('   ', [])).toBe(false)
    expect(hasContent(' Идём ', [])).toBe(true)
    expect(hasContent('', [photo()])).toBe(true)
  })
})

describe('validateMessage', () => {
  it('accepts text with up to 10 photos', () => {
    const photos = Array.from({ length: 10 }, (_, i) => photo(`${i}.jpg`))
    expect(validateMessage('Готово', photos)).toBeNull()
  })

  it('accepts a single document', () => {
    expect(validateMessage('', [pdf()])).toBeNull()
  })

  it('rejects text over 3000 characters', () => {
    expect(validateMessage('а'.repeat(3001), [])).toBe('Сообщение длиннее 3000 символов')
  })

  it('rejects more than 10 photos', () => {
    const photos = Array.from({ length: 11 }, (_, i) => photo(`${i}.jpg`))
    expect(validateMessage('', photos)).toBe('Можно приложить не больше 10 фото')
  })

  it('rejects a document together with other files', () => {
    expect(validateMessage('', [pdf(), photo()])).toBe(
      'Документ отправляется один, без других файлов',
    )
  })

  it('rejects files over 20 MB', () => {
    expect(validateMessage('', [photo('big.jpg', 25 * MB)])).toBe('Файл «big.jpg» больше 20 МБ')
  })
})
