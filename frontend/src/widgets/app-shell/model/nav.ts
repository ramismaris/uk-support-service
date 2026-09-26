import { isAdmin, type User } from '@/entities/user'
import { routePaths } from '@/shared/config'

export interface NavItem {
  key: string
  label: string
  // null — the section is not built yet (Ф5): shown, but inactive.
  to: string | null
  adminOnly: boolean
}

const navItems: NavItem[] = [
  { key: 'tickets', label: 'Обращения', to: routePaths.staff, adminOnly: false },
  { key: 'content', label: 'Контент', to: null, adminOnly: true },
  { key: 'users', label: 'Пользователи', to: null, adminOnly: true },
]

export function visibleNavItems(user: User): NavItem[] {
  return navItems.filter((item) => !item.adminOnly || isAdmin(user))
}
