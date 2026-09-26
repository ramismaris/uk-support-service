import { NavLink, Outlet } from 'react-router'
import { useMe } from '@/entities/session'
import { getDisplayName, roleLabels } from '@/entities/user'
import { LogoutButton } from '@/features/logout'
import { visibleNavItems, type NavItem } from '../model/nav'

const DISABLED_HINT = 'Раздел появится позже'

function SideLink({ item }: { item: NavItem }) {
  if (item.to === null) {
    return (
      <span
        className="rounded-lg px-3 py-2 text-neutral-400"
        aria-disabled="true"
        title={DISABLED_HINT}
      >
        {item.label}
      </span>
    )
  }
  return (
    <NavLink
      to={item.to}
      end
      className={({ isActive }) =>
        `rounded-lg px-3 py-2 transition-colors ${
          isActive
            ? 'bg-brand/10 font-medium text-brand'
            : 'hover:bg-neutral-100 dark:hover:bg-neutral-900'
        }`
      }
    >
      {item.label}
    </NavLink>
  )
}

function TabLink({ item }: { item: NavItem }) {
  const base = 'flex flex-1 items-center justify-center py-3 text-xs'
  if (item.to === null) {
    return (
      <span className={`${base} text-neutral-400`} aria-disabled="true" title={DISABLED_HINT}>
        {item.label}
      </span>
    )
  }
  return (
    <NavLink
      to={item.to}
      end
      className={({ isActive }) => `${base} ${isActive ? 'font-medium text-brand' : ''}`}
    >
      {item.label}
    </NavLink>
  )
}

export function AppShell() {
  const { data: user } = useMe()
  if (!user) {
    return null
  }
  const items = visibleNavItems(user)
  const name = getDisplayName(user)

  return (
    <div className="flex min-h-dvh">
      <aside className="hidden w-64 shrink-0 flex-col gap-6 border-r border-neutral-200 p-4 lg:flex dark:border-neutral-800">
        <div className="px-3 text-lg font-semibold">Панель УК</div>
        <nav className="flex flex-col gap-1">
          {items.map((item) => (
            <SideLink key={item.key} item={item} />
          ))}
        </nav>
        <div className="mt-auto flex flex-col items-start gap-2 px-3 text-sm">
          <div>
            <div className="font-medium">{name}</div>
            <div className="text-neutral-500">{roleLabels[user.role]}</div>
          </div>
          <LogoutButton />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-neutral-200 px-4 py-2 lg:hidden dark:border-neutral-800">
          <span className="text-sm font-medium">{name}</span>
          <LogoutButton />
        </header>
        <main className="flex-1 pb-[calc(3rem+env(safe-area-inset-bottom))] lg:pb-0">
          <Outlet />
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 flex border-t border-neutral-200 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden dark:border-neutral-800 dark:bg-neutral-900">
        {items.map((item) => (
          <TabLink key={item.key} item={item} />
        ))}
      </nav>
    </div>
  )
}
