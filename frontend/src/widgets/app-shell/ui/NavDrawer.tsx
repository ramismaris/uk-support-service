import { AnimatePresence, motion } from 'framer-motion'
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

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-black/40 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
          />
          <motion.aside
            className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col gap-6 bg-white p-4 pt-[calc(1rem+env(safe-area-inset-top))] shadow-xl lg:hidden dark:bg-neutral-900"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'tween', duration: 0.2 }}
          >
            <button
              type="button"
              aria-label="Закрыть меню"
              onClick={() => setOpen(false)}
              className="absolute top-3 right-3 rounded-full p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              <X size={20} strokeWidth={2} />
            </button>
            <NavContent user={user} onNavigate={() => setOpen(false)} />
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
