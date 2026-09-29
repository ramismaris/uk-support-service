import { describe, expect, it } from 'vitest'
import { plural } from './plural'

const resident = (n: number) => plural(n, 'жилец', 'жильца', 'жильцов')

describe('plural', () => {
  it.each([
    [1, 'жилец'],
    [2, 'жильца'],
    [4, 'жильца'],
    [5, 'жильцов'],
    [11, 'жильцов'],
    [12, 'жильцов'],
    [21, 'жилец'],
    [22, 'жильца'],
    [25, 'жильцов'],
    [101, 'жилец'],
    [111, 'жильцов'],
    [0, 'жильцов'],
  ])('%i → %s', (n, word) => {
    expect(resident(n)).toBe(word)
  })
})
