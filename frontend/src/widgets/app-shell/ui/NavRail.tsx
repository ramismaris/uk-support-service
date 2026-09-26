import { NavLink } from 'react-router'
import { getDisplayName, roleLabels, type User } from '@/entities/user'
import { visibleNavItems } from '../model/nav'
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
  return (
    <aside className="hidden w-16 shrink-0 flex-col items-center gap-2 border-r border-line py-3 lg:flex">
      <nav className="flex flex-col items-center gap-1">
        {visibleNavItems(user).map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.key}
              to={item.to}
              title={item.label}
              aria-label={item.label}
              className={({ isActive }) =>
                `flex size-10 items-center justify-center rounded-xl transition-colors ${
                  isActive ? 'bg-brand/12 text-brand' : 'text-fg-2 hover:bg-hover'
                }`
              }
            >
              <Icon size={22} strokeWidth={2} />
            </NavLink>
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
