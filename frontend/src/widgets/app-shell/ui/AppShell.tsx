import { Outlet } from 'react-router'
import { useMe } from '@/entities/session'
import { NavContent } from './NavContent'
import { NavDrawer } from './NavDrawer'

export function AppShell() {
  const { data: user } = useMe()
  if (!user) {
    return null
  }

  return (
    <div className="flex h-dvh">
      <aside className="hidden w-64 shrink-0 flex-col gap-6 border-r border-line p-4 lg:flex">
        <NavContent user={user} />
      </aside>
      {/* Phones: navigation is a drawer opened from the page header (NavMenuButton). */}
      <NavDrawer user={user} />
      <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden pb-[env(safe-area-inset-bottom)] lg:pb-0">
        <Outlet />
      </main>
    </div>
  )
}
