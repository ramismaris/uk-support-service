import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchInsights, refreshInsights, type Period } from '../api/dashboard'

const STALE_MS = 5 * 60 * 1000

const insightsKey = (period: Period) => ['admin', 'dashboard', 'insights', period] as const

export function useInsights(period: Period) {
  return useQuery({
    queryKey: insightsKey(period),
    queryFn: () => fetchInsights(period),
    staleTime: STALE_MS,
  })
}

export function useRefreshInsights(period: Period) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => refreshInsights(period),
    onSuccess: (data) => queryClient.setQueryData(insightsKey(period), data),
  })
}
