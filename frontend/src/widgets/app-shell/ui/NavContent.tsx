import { FileText, MessagesSquare, Users, type LucideIcon } from 'lucide-react'
import { NavLink } from 'react-router'
import { getDisplayName, roleLabels, type User } from '@/entities/user'
import { visibleNavItems, type NavItem } from '../model/nav'
import { LogoutButton } from './LogoutButton'

const icons: Record<string, LucideIcon> = {
  tickets: MessagesSquare,
  content: FileText,
  users: Users,
}

function NavEntry({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const Icon = icons[item.key] ?? MessagesSquare
  const inner = (
    <>
      <Icon size={20} strokeWidth={2} className="shrink-0" />
      <span className="flex-1">{item.label}</span>
    </>
  )
  if (item.to === null) {
    return (
      <span
        className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-fg-3"
        aria-disabled="true"
      >
        {inner}
        <span className="rounded-full bg-fill px-2 py-0.5 text-[11px] text-fg-3">Скоро</span>
      </span>
    )
  }
  return (
    <NavLink
      to={item.to}
      onClick={onNavigate}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors ${
          isActive ? 'bg-brand/10 font-medium text-brand' : 'hover:bg-hover'
        }`
      }
    >
      {inner}
    </NavLink>
  )
}

interface NavContentProps {
  user: User
  // Closes the phone drawer after a section is picked.
  onNavigate?: () => void
}

export function NavContent({ user, onNavigate }: NavContentProps) {
  return (
    <>
      <div className="px-3 text-lg font-semibold">Панель УК</div>
      <nav className="flex flex-col gap-1">
        {visibleNavItems(user).map((item) => (
          <NavEntry key={item.key} item={item} onNavigate={onNavigate} />
        ))}
      </nav>
      <div className="mt-auto flex flex-col items-start gap-2 px-3 text-sm">
        <div>
          <div className="font-medium">{getDisplayName(user)}</div>
          <div className="text-fg-3">{roleLabels[user.role]}</div>
        </div>
        <LogoutButton />
      </div>
    </>
  )
}
