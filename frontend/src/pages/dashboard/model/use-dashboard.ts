import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { fetchDashboard, type Period } from '../api/dashboard'

export function useDashboard(period: Period) {
  return useQuery({
    queryKey: ['admin', 'dashboard', period],
    queryFn: () => fetchDashboard(period),
    // Switching the period keeps the old numbers on screen until the new ones arrive.
    placeholderData: keepPreviousData,
  })
}
