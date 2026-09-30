import { describe, expect, it } from 'vitest'
import { moveId } from './order'

describe('moveId', () => {
  it('moves an id one place down', () => {
    expect(moveId([1, 2, 3], 1, 1)).toEqual([2, 1, 3])
  })

  it('moves an id one place up', () => {
    expect(moveId([1, 2, 3], 3, -1)).toEqual([1, 3, 2])
  })

  it('stays put at the edges', () => {
    expect(moveId([1, 2, 3], 1, -1)).toEqual([1, 2, 3])
    expect(moveId([1, 2, 3], 3, 1)).toEqual([1, 2, 3])
  })

  it('ignores an id that is not in the list', () => {
    expect(moveId([1, 2, 3], 9, 1)).toEqual([1, 2, 3])
  })

  it('does not change the original list', () => {
    const ids = [1, 2, 3]
    moveId(ids, 2, 1)
    expect(ids).toEqual([1, 2, 3])
  })
})
