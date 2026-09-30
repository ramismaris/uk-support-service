import { api, unwrap, type components } from '@/shared/api'

// Buildings and categories look alike to the page: a name, an on/off switch and an id.
export interface DirectoryItem {
  id: number
  name: string
  active: boolean
}

type AdminBuilding = components['schemas']['AdminBuildingResponse']
type AdminCategory = components['schemas']['AdminCategoryResponse']

const fromBuilding = (item: AdminBuilding): DirectoryItem => ({
  id: item.id,
  name: item.address,
  active: item.is_active,
})

const fromCategory = (item: AdminCategory): DirectoryItem => ({
  id: item.id,
  name: item.title,
  active: item.is_active,
})

export async function fetchBuildings(): Promise<DirectoryItem[]> {
  return (await unwrap(api.GET('/api/v1/admin/buildings'))).map(fromBuilding)
}

export async function createBuilding(address: string): Promise<DirectoryItem> {
  return fromBuilding(await unwrap(api.POST('/api/v1/admin/buildings', { body: { address } })))
}

export async function updateBuilding(
  id: number,
  change: { name?: string; active?: boolean },
): Promise<DirectoryItem> {
  return fromBuilding(
    await unwrap(
      api.PATCH('/api/v1/admin/buildings/{building_id}', {
        params: { path: { building_id: id } },
        body: { address: change.name, is_active: change.active },
      }),
    ),
  )
}

export async function fetchCategories(): Promise<DirectoryItem[]> {
  return (await unwrap(api.GET('/api/v1/admin/categories'))).map(fromCategory)
}

export async function createCategory(title: string): Promise<DirectoryItem> {
  return fromCategory(await unwrap(api.POST('/api/v1/admin/categories', { body: { title } })))
}

export async function updateCategory(
  id: number,
  change: { name?: string; active?: boolean },
): Promise<DirectoryItem> {
  return fromCategory(
    await unwrap(
      api.PATCH('/api/v1/admin/categories/{category_id}', {
        params: { path: { category_id: id } },
        body: { title: change.name, is_active: change.active },
      }),
    ),
  )
}

export async function reorderCategories(ids: number[]): Promise<DirectoryItem[]> {
  return (await unwrap(api.PUT('/api/v1/admin/categories/order', { body: { ids } }))).map(
    fromCategory,
  )
}
