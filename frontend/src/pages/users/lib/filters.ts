import type { components } from '@/shared/api'

type UserRole = components['schemas']['UserRole']

export const USER_FILTERS = ['all', 'staff', 'residents', 'blocked'] as const
export type UserFilter = (typeof USER_FILTERS)[number]

export const userFilterLabels: Record<UserFilter, string> = {
  all: 'Все',
  staff: 'Сотрудники',
  residents: 'Жильцы',
  blocked: 'Заблокированные',
}

export interface UserSearch {
  filter: UserFilter
  q: string
}

export interface UserQuery {
  role?: UserRole[]
  is_blocked?: boolean
  q?: string
}

export function userFilterToQuery(filter: UserFilter, q: string): UserQuery {
  const query: UserQuery = {}
  if (filter === 'staff') {
    query.role = ['MANAGER', 'ADMIN']
  } else if (filter === 'residents') {
    query.role = ['CLIENT']
  } else if (filter === 'blocked') {
    query.is_blocked = true
  }
  const search = q.trim()
  if (search) {
    query.q = search
  }
  return query
}

export function parseUserSearch(params: URLSearchParams): UserSearch {
  const filter = params.get('filter')
  return {
    filter: USER_FILTERS.includes(filter as UserFilter) ? (filter as UserFilter) : 'all',
    q: params.get('q') ?? '',
  }
}

export function userSearchToParams({ filter, q }: UserSearch): URLSearchParams {
  const params = new URLSearchParams()
  if (filter !== 'all') {
    params.set('filter', filter)
  }
  if (q) {
    params.set('q', q)
  }
  return params
}
