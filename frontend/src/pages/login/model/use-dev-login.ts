import { useMutation } from '@tanstack/react-query'
import { useStartSession } from '@/entities/session'
import { devLogin } from '../api/dev-login'

export function useDevLogin() {
  const startSession = useStartSession()
  return useMutation({
    mutationFn: devLogin,
    onSuccess: ({ token, user }) => startSession(token, user),
  })
}
