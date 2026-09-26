import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'

interface DetailsDrawerProps {
  open: boolean
  onClose: () => void
  children: ReactNode
}

export function DetailsDrawer({ open, onClose, children }: DetailsDrawerProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-black/30"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed inset-y-0 right-0 z-50 w-96 max-w-full overflow-y-auto bg-white shadow-xl dark:bg-neutral-900"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'tween', duration: 0.2 }}
          >
            <button
              type="button"
              aria-label="Закрыть"
              onClick={onClose}
              className="absolute top-3 right-3 rounded-full p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              <X size={20} strokeWidth={2} />
            </button>
            {children}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
