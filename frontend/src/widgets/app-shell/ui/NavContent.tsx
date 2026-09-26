import { Link, useLocation } from 'react-router'
import { getDisplayName, roleLabels, type User } from '@/entities/user'
import { isNavItemActive, visibleNavItems, type VisibleNavItem } from '../model/nav'
import { BrandMark } from './BrandMark'
import { LogoutButton } from './LogoutButton'

function NavEntry({ item, onNavigate }: { item: VisibleNavItem; onNavigate?: () => void }) {
  const Icon = item.icon
  const active = isNavItemActive(item, useLocation().pathname)
  return (
    <Link
      to={item.to}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      className={`flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors ${
        active ? 'bg-brand/12 font-medium text-brand' : 'hover:bg-hover'
      }`}
    >
      <Icon size={20} strokeWidth={2} className="shrink-0" />
      {item.label}
    </Link>
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
      <div className="px-1 pr-10">
        <BrandMark withName />
      </div>
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
