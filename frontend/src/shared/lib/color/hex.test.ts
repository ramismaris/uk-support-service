import { describe, expect, it } from 'vitest'
import { parseHexColor } from './hex'

describe('parseHexColor', () => {
  it('parses #RRGGBB in any case', () => {
    expect(parseHexColor('#007AFF')).toEqual([0, 122 / 255, 1])
    expect(parseHexColor('#ffffff')).toEqual([1, 1, 1])
  })

  it.each(['', '007aff', '#07f', '#GGGGGG', '#007aff00', ' #007aff'])('rejects %j', (value) => {
    expect(parseHexColor(value)).toBeNull()
  })
})
