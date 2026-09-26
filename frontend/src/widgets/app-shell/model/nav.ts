import { FileText, MessagesSquare, Users, type LucideIcon } from 'lucide-react'
import { isAdmin, type User } from '@/entities/user'
import { routePaths } from '@/shared/config'

export interface NavItem {
  key: string
  label: string
  icon: LucideIcon
  // null — the section is not built yet (Ф5): hidden from the menu.
  to: string | null
  adminOnly: boolean
}

export type VisibleNavItem = NavItem & { to: string }

const navItems: NavItem[] = [
  {
    key: 'tickets',
    label: 'Обращения',
    icon: MessagesSquare,
    to: routePaths.staff,
    adminOnly: false,
  },
  { key: 'content', label: 'Контент', icon: FileText, to: null, adminOnly: true },
  { key: 'users', label: 'Пользователи', icon: Users, to: null, adminOnly: true },
]

export function visibleNavItems(user: User): VisibleNavItem[] {
  return navItems.filter(
    (item): item is VisibleNavItem => item.to !== null && (!item.adminOnly || isAdmin(user)),
  )
}
