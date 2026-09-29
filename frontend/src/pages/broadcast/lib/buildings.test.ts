import { describe, expect, it } from 'vitest'
import { filterBuildings, toggleId } from './buildings'

const buildings = [
  { id: 1, address: 'ул. Ленина, 5' },
  { id: 2, address: 'пр. Мира, 12' },
  { id: 3, address: 'ул. Ленинградская, 1' },
]

describe('filterBuildings', () => {
  it('keeps everything for an empty query', () => {
    expect(filterBuildings(buildings, '  ')).toEqual(buildings)
  })

  it('matches part of the address, ignoring case', () => {
    expect(filterBuildings(buildings, 'ЛЕНИН').map((building) => building.id)).toEqual([1, 3])
    expect(filterBuildings(buildings, 'мира')).toEqual([buildings[1]])
  })

  it('finds nothing for an unknown address', () => {
    expect(filterBuildings(buildings, 'zzz')).toEqual([])
  })
})

describe('toggleId', () => {
  it('adds an id that is not selected', () => {
    expect(toggleId([1], 2)).toEqual([1, 2])
  })

  it('removes an id that is selected', () => {
    expect(toggleId([1, 2], 1)).toEqual([2])
  })

  it('does not change the original list', () => {
    const selected = [1]
    toggleId(selected, 2)
    expect(selected).toEqual([1])
  })
})
