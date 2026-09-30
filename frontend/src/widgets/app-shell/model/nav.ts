import {
  ChartColumn,
  Library,
  Megaphone,
  MessageSquareText,
  MessagesSquare,
  Palette,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { isAdmin, type User } from '@/entities/user'
import { routePaths } from '@/shared/config'

export interface NavItem {
  key: string
  label: string
  icon: LucideIcon
  // null — the section is not built yet (Ф5): hidden from the menu.
  to: string | null
  adminOnly: boolean
  // Extra path prefixes that belong to this section (tickets live under /staff/tickets).
  alsoActiveOn?: string[]
}

export type VisibleNavItem = NavItem & { to: string }

const navItems: NavItem[] = [
  {
    key: 'dashboard',
    label: 'Дашборд',
    icon: ChartColumn,
    to: routePaths.dashboard,
    adminOnly: true,
  },
  {
    key: 'tickets',
    label: 'Обращения',
    icon: MessagesSquare,
    to: routePaths.staff,
    adminOnly: false,
    alsoActiveOn: ['/staff/tickets'],
  },
  {
    key: 'broadcast',
    label: 'Рассылка',
    icon: Megaphone,
    to: routePaths.broadcast,
    adminOnly: true,
  },
  {
    key: 'content',
    label: 'Контент бота',
    icon: MessageSquareText,
    to: routePaths.content,
    adminOnly: true,
  },
  {
    key: 'directories',
    label: 'Справочники',
    icon: Library,
    to: routePaths.directories,
    adminOnly: true,
  },
  { key: 'users', label: 'Пользователи', icon: Users, to: routePaths.users, adminOnly: true },
  {
    key: 'appearance',
    label: 'Оформление',
    icon: Palette,
    to: routePaths.appearance,
    adminOnly: true,
  },
]

export function visibleNavItems(user: User): VisibleNavItem[] {
  return navItems.filter(
    (item): item is VisibleNavItem => item.to !== null && (!item.adminOnly || isAdmin(user)),
  )
}

function underPath(pathname: string, base: string): boolean {
  return pathname === base || pathname.startsWith(`${base}/`)
}

// /staff is a prefix of every admin section, so section links cannot rely on NavLink's matching.
export function isNavItemActive(item: VisibleNavItem, pathname: string): boolean {
  if (pathname === item.to) {
    return true
  }
  if (item.alsoActiveOn?.some((prefix) => underPath(pathname, prefix))) {
    return true
  }
  return item.to !== routePaths.staff && underPath(pathname, item.to)
}
