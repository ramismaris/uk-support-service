import type { StaffBuilding } from '@/entities/directory'

export function filterBuildings(buildings: StaffBuilding[], query: string): StaffBuilding[] {
  const needle = query.trim().toLowerCase()
  if (needle === '') {
    return buildings
  }
  return buildings.filter((building) => building.address.toLowerCase().includes(needle))
}

export function toggleId(ids: number[], id: number): number[] {
  return ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id]
}
