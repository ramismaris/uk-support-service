import { useQuery } from '@tanstack/react-query'
import { api, unwrap } from '@/shared/api'
import { useSessionStore } from '../model/session-store'

export const meQueryKey = ['me'] as const

export function fetchMe() {
  return unwrap(api.GET('/api/v1/me'))
}

export function useMe() {
  const token = useSessionStore((state) => state.token)
  return useQuery({ queryKey: meQueryKey, queryFn: fetchMe, enabled: token !== null })
}
