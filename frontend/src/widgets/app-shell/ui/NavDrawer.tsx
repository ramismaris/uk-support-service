import { motion, useReducedMotion } from 'framer-motion'
import { X } from 'lucide-react'
import { useEffect } from 'react'
import { useLocation } from 'react-router'
import type { User } from '@/entities/user'
import { useNavDrawer } from '../model/nav-drawer'
import { NavContent } from './NavContent'

export function NavDrawer({ user }: { user: User }) {
  const { open, setOpen } = useNavDrawer()
  const { pathname } = useLocation()
  const reduced = useReducedMotion() ?? false
  const transition = reduced
    ? { duration: 0 }
    : { type: 'tween' as const, ease: 'easeOut' as const, duration: 0.2 }

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

  // Always mounted, so the menu is not built mid-animation. Only transform and opacity animate:
  // framer-motion hands those to the browser (WAAPI), so rendering the next page on tap does not
  // stall the drawer the way the per-frame `x` animation did.
  return (
    <div className="lg:hidden">
      <motion.div
        aria-hidden
        className={`fixed inset-0 z-40 bg-overlay ${open ? '' : 'pointer-events-none'}`}
        initial={false}
        animate={{ opacity: open ? 1 : 0 }}
        transition={transition}
        onClick={() => setOpen(false)}
      />
      <motion.aside
        inert={!open}
        className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col gap-6 bg-layer p-4 pt-[calc(1rem+env(safe-area-inset-top))]"
        initial={false}
        animate={{ transform: open ? 'translateX(0%)' : 'translateX(-100%)' }}
        transition={transition}
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
      </motion.aside>
    </div>
  )
}
