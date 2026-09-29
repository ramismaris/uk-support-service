import type { DashboardCategory } from '../api/dashboard'

export interface CategoryRow {
  id: number
  title: string
  created: number
  share: number
  hours: number | null
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
