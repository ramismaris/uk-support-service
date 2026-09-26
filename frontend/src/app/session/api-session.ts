import { useSessionStore } from '@/entities/session'
import { queryClient, setTokenGetter, setUnauthorizedHandler } from '@/shared/api'

setTokenGetter(() => useSessionStore.getState().token)

setUnauthorizedHandler(() => {
  useSessionStore.getState().clear()
  queryClient.clear()
})
