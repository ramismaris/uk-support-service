import { api, unwrap, type components } from '@/shared/api'

export type Dashboard = components['schemas']['DashboardResponse']
export type DashboardDay = components['schemas']['DashboardDay']
export type DashboardCategory = components['schemas']['DashboardCategory']

export type Insights = components['schemas']['InsightsResponse']
export type InsightItem = components['schemas']['InsightItem']

export const PERIODS = [7, 30, 90] as const
export type Period = (typeof PERIODS)[number]

export function fetchDashboard(period: Period) {
  return unwrap(api.GET('/api/v1/admin/dashboard', { params: { query: { period } } }))
}

export function fetchInsights(period: Period) {
  return unwrap(api.GET('/api/v1/admin/dashboard/insights', { params: { query: { period } } }))
}

export function refreshInsights(period: Period) {
  return unwrap(api.POST('/api/v1/admin/dashboard/insights', { params: { query: { period } } }))
}
