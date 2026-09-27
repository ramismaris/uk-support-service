import { Link, useLocation } from 'react-router'
import { useUnreadCount } from '@/entities/ticket'
import { getDisplayName, roleLabels, type User } from '@/entities/user'
import { unreadBadge } from '../lib/unread'
import { isNavItemActive, visibleNavItems } from '../model/nav'
import { BrandMark } from './BrandMark'
import { LogoutButton } from './LogoutButton'

function initials(user: User): string {
  return [user.first_name, user.last_name]
    .filter(Boolean)
    .map((part) => part!.charAt(0))
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

// Desktop navigation: a narrow rail, so the chat gets the width.
export function NavRail({ user }: { user: User }) {
  const who = `${getDisplayName(user)} · ${roleLabels[user.role]}`
  const { pathname } = useLocation()
  const unread = unreadBadge(useUnreadCount().data ?? 0)
  return (
    <aside className="hidden w-16 shrink-0 flex-col items-center gap-2 border-r border-line py-3 lg:flex">
      <div className="mb-2">
        <BrandMark />
      </div>
      <nav className="flex flex-col items-center gap-1">
        {visibleNavItems(user).map((item) => {
          const Icon = item.icon
          return (
            <Link
              key={item.key}
              to={item.to}
              title={item.label}
              aria-label={item.label}
              aria-current={isNavItemActive(item, pathname) ? 'page' : undefined}
              className={`relative flex size-10 items-center justify-center rounded-xl transition-colors ${
                isNavItemActive(item, pathname)
                  ? 'bg-brand/12 text-brand'
                  : 'text-fg-2 hover:bg-hover'
              }`}
            >
              <Icon size={22} strokeWidth={2} />
              {item.key === 'tickets' && unread && (
                <span
                  aria-label={`Непрочитанных: ${unread}`}
                  className="absolute -top-1 -right-1 flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-brand px-1 text-[11px] leading-none font-semibold text-white ring-2 ring-surface"
                >
                  {unread}
                </span>
              )}
            </Link>
          )
        })}
      </nav>
      <div className="mt-auto flex flex-col items-center gap-1">
        <span
          title={who}
          aria-label={who}
          className="flex size-9 items-center justify-center rounded-full bg-fill text-xs font-medium text-fg-2"
        >
          {initials(user)}
        </span>
        <LogoutButton compact />
      </div>
    </aside>
  )
}
