import { useQueryClient } from '@tanstack/react-query'
import type { components } from '@/shared/api'
import { meQueryKey } from '../api/me'
import { useSessionStore } from './session-store'

type User = components['schemas']['UserResponse']

export function useStartSession(): (token: string, user: User) => void {
  const queryClient = useQueryClient()
  const setToken = useSessionStore((state) => state.setToken)
  return (token, user) => {
    // User first: once the token appears, the session gate already has /me data.
    queryClient.setQueryData(meQueryKey, user)
    setToken(token)
  }
}
