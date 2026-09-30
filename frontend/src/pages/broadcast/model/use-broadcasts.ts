import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createBroadcast,
  fetchAudience,
  fetchBroadcasts,
  type BroadcastRequest,
} from '../api/broadcasts'

const POLL_MS = 2000

const keys = {
  history: ['admin', 'broadcasts'] as const,
  audience: (ids: number[] | null) =>
    ['admin', 'broadcasts', 'audience', ids ? [...ids].sort((a, b) => a - b) : 'all'] as const,
}

export function useBroadcasts() {
  return useQuery({
    queryKey: keys.history,
    queryFn: fetchBroadcasts,
    refetchInterval: (query) =>
      query.state.data?.items.some((item) => item.status === 'SENDING') ? POLL_MS : false,
  })
}

// null asks for everyone; an empty selection has no audience to count.
export function useAudience(buildingIds: number[] | null) {
  return useQuery({
    queryKey: keys.audience(buildingIds),
    queryFn: () => fetchAudience(buildingIds),
    enabled: buildingIds === null || buildingIds.length > 0,
    placeholderData: keepPreviousData,
  })
}

export function useSendBroadcast() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: BroadcastRequest) => createBroadcast(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.history }),
  })
}
