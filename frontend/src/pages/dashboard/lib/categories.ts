import type { DashboardCategory } from '../api/dashboard'

export interface CategoryRow {
  id: number
  title: string
  created: number
  // Of all requests in the period, 0..1.
  share: number
  hours: number | null
  // Solving takes longer than the norm.
  slow: boolean
}

export function categoryRows(categories: DashboardCategory[], slaHours: number): CategoryRow[] {
  const total = categories.reduce((sum, category) => sum + category.created, 0)
  return categories.map((category) => ({
    id: category.category_id,
    title: category.title,
    created: category.created,
    share: total > 0 ? category.created / total : 0,
    hours: category.resolution_hours,
    slow: category.resolution_hours !== null && category.resolution_hours > slaHours,
  }))
}
