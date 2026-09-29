import { useEffect } from 'react'
import { Outlet } from 'react-router'
import { useMe } from '@/entities/session'
import { useUnreadCount } from '@/entities/ticket'
import { withUnreadCount } from '../lib/unread'
import { NavDrawer } from './NavDrawer'
import { NavRail } from './NavRail'

// The theme rewrites the title on its own schedule, so the count re-applies after every change.
function useUnreadTitle(count: number) {
  useEffect(() => {
    const apply = () => {
      const next = withUnreadCount(document.title, count)
      if (next !== document.title) {
        document.title = next
      }
    }
    apply()
    const title = document.querySelector('title')
    const observer = new MutationObserver(apply)
    if (title) {
      observer.observe(title, { childList: true })
    }
    return () => {
      observer.disconnect()
      document.title = withUnreadCount(document.title, 0)
    }
  }, [count])
}

export function AppShell() {
  const { data: user } = useMe()
  useUnreadTitle(useUnreadCount().data ?? 0)
  if (!user) {
    return null
  }

  return (
    // Holds the sr-only unread labels, which would otherwise stretch the document.
    <div className="relative flex h-dvh overflow-hidden">
      <NavRail user={user} />
      {/* Phones: navigation is a drawer opened from the page header (NavMenuButton). */}
      <NavDrawer user={user} />
      <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden pb-[env(safe-area-inset-bottom)] lg:pb-0">
        <Outlet />
      </main>
    </div>
  )
}
