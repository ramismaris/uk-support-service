import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { useSessionStore } from '@/entities/session'
import { routePaths } from '@/shared/config'
import { logout } from '../api/logout'

export function useLogout() {
  const queryClient = useQueryClient()
  const clear = useSessionStore((state) => state.clear)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: logout,
    // Leave locally even if the server call fails: the user asked to sign out.
    onSettled: () => {
      clear()
      queryClient.clear()
      navigate(routePaths.login, { replace: true })
    },
  })
}
