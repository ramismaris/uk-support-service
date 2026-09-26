import { Outlet } from 'react-router'
import { useMe } from '@/entities/session'
import { NavDrawer } from './NavDrawer'
import { NavRail } from './NavRail'

export function AppShell() {
  const { data: user } = useMe()
  if (!user) {
    return null
  }

  return (
    <div className="flex h-dvh">
      <NavRail user={user} />
      {/* Phones: navigation is a drawer opened from the page header (NavMenuButton). */}
      <NavDrawer user={user} />
      <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden pb-[env(safe-area-inset-bottom)] lg:pb-0">
        <Outlet />
      </main>
    </div>
  )
}
