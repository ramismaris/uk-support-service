import { useQuery } from '@tanstack/react-query'
import { api, unwrap, type components } from '@/shared/api'

export type StaffBuilding = components['schemas']['BuildingShortResponse']
export type StaffCategory = components['schemas']['CategoryShortResponse']

// Only the enabled ones, in the bot's order. The admin's directories page refreshes these keys.
export const directoryKeys = {
  buildings: ['staff', 'buildings'] as const,
  categories: ['staff', 'categories'] as const,
}

export function useStaffBuildings() {
  return useQuery({
    queryKey: directoryKeys.buildings,
    queryFn: () => unwrap(api.GET('/api/v1/staff/buildings')),
  })
}

export function useStaffCategories() {
  return useQuery({
    queryKey: directoryKeys.categories,
    queryFn: () => unwrap(api.GET('/api/v1/staff/categories')),
  })
}
