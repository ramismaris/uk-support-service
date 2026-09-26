import { describe, expect, it } from 'vitest'
import { formatFileSize } from './file-size'

describe('formatFileSize', () => {
  it.each([
    [512, '512 Б'],
    [2048, '2 КБ'],
    [1536000, '1,5 МБ'],
    [20 * 1024 * 1024, '20 МБ'],
  ])('%i → %s', (bytes, text) => {
    expect(formatFileSize(bytes)).toBe(text)
  })
})
