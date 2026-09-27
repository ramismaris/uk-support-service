import { X } from 'lucide-react'
import { useEffect } from 'react'
import { useLocation } from 'react-router'
import type { User } from '@/entities/user'
import { useNavDrawer } from '../model/nav-drawer'
import { NavContent } from './NavContent'

export function NavDrawer({ user }: { user: User }) {
  const { open, setOpen } = useNavDrawer()
  const { pathname } = useLocation()

  useEffect(() => setOpen(false), [pathname, setOpen])

  useEffect(() => {
    if (!open) {
      return
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, setOpen])

  // Always mounted and moved by CSS transitions: the compositor runs them, so rendering the
  // next page on tap does not make the drawer stutter the way a JS-driven animation did.
  return (
    <div className="lg:hidden">
      <div
        aria-hidden
        className={`fixed inset-0 z-40 bg-overlay transition-opacity duration-200 motion-reduce:transition-none ${
          open ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={() => setOpen(false)}
      />
      <aside
        inert={!open}
        className={`fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col gap-6 bg-layer p-4 pt-[calc(1rem+env(safe-area-inset-top))] transition-transform duration-200 ease-out will-change-transform motion-reduce:transition-none ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <button
          type="button"
          aria-label="Закрыть меню"
          onClick={() => setOpen(false)}
          className="absolute top-3 right-3 rounded-full p-1.5 hover:bg-hover"
        >
          <X size={20} strokeWidth={2} />
        </button>
        <NavContent user={user} onNavigate={() => setOpen(false)} />
      </aside>
    </div>
  )
}
