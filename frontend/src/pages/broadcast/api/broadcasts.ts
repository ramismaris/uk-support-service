import { api, unwrap, type components } from '@/shared/api'

export type Broadcast = components['schemas']['BroadcastResponse']
export type BroadcastRequest = components['schemas']['BroadcastCreateRequest']
export type BroadcastStatus = components['schemas']['BroadcastStatus']
export type Building = components['schemas']['BuildingShortResponse']

const HISTORY_LIMIT = 20

export function fetchBroadcasts() {
  return unwrap(
    api.GET('/api/v1/admin/broadcasts', { params: { query: { skip: 0, limit: HISTORY_LIMIT } } }),
  )
}

export function fetchAudience(buildingIds: number[] | null) {
  return unwrap(
    api.GET('/api/v1/admin/broadcasts/audience', {
      params: { query: { building_id: buildingIds ?? undefined } },
    }),
  )
}

export function fetchBuildings() {
  return unwrap(api.GET('/api/v1/staff/buildings'))
}

export function createBroadcast(body: BroadcastRequest) {
  return unwrap(api.POST('/api/v1/admin/broadcasts', { body }))
}
