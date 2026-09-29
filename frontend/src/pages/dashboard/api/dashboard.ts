import { api, unwrap, type components } from '@/shared/api'

export type Dashboard = components['schemas']['DashboardResponse']
export type DashboardDay = components['schemas']['DashboardDay']
export type DashboardCategory = components['schemas']['DashboardCategory']

export const PERIODS = [7, 30, 90] as const
export type Period = (typeof PERIODS)[number]

export function fetchDashboard(period: Period) {
  return unwrap(api.GET('/api/v1/admin/dashboard', { params: { query: { period } } }))
}
