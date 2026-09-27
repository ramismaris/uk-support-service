import { describe, expect, it } from 'vitest'
import { isPhoto } from './photo'

describe('isPhoto', () => {
  it('tells photos from documents by mime type', () => {
    expect(isPhoto({ mime: 'image/png' })).toBe(true)
    expect(isPhoto({ mime: 'application/pdf' })).toBe(false)
  })
})
