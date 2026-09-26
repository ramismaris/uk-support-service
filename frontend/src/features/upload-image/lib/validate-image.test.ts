import { describe, expect, it } from 'vitest'
import { validateImage } from './validate-image'

const MB = 1024 * 1024

describe('validateImage', () => {
  it.each(['image/jpeg', 'image/png'])('accepts %s', (type) => {
    expect(validateImage({ type, size: MB })).toBeNull()
  })

  it.each(['image/webp', 'image/gif', 'image/svg+xml', 'application/pdf'])('rejects %s', (type) => {
    expect(validateImage({ type, size: MB })).toBe('Только JPEG или PNG')
  })

  it('rejects files over 20 MB', () => {
    expect(validateImage({ type: 'image/png', size: 21 * MB })).toBe('Файл больше 20 МБ')
  })
})
