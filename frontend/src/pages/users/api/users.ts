import { api, unwrap, type components } from '@/shared/api'
import type { UserQuery } from '../lib/filters'

export type AdminUser = components['schemas']['AdminUserResponse']
export type UserUpdate = components['schemas']['UserUpdateRequest']

export const PAGE_SIZE = 50

export function fetchUsers(query: UserQuery, skip: number) {
  return unwrap(
    api.GET('/api/v1/admin/users', { params: { query: { ...query, skip, limit: PAGE_SIZE } } }),
  )
}

export function updateUser(id: number, update: UserUpdate) {
  return unwrap(
    api.PATCH('/api/v1/admin/users/{user_id}', {
      params: { path: { user_id: id } },
      body: update,
    }),
  )
}
