import { useMutation } from '@tanstack/react-query'
import { useStartSession } from '@/entities/session'
import { getInitData } from '@/shared/lib/max-bridge'
import { loginByMax } from '../api/login-by-max'

export function useLoginByMax() {
  const startSession = useStartSession()
  return useMutation({
    mutationFn: () => loginByMax(getInitData()),
    onSuccess: ({ token, user }) => startSession(token, user),
  })
}
