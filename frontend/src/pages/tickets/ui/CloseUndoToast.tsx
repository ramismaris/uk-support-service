import { AnimatePresence, motion } from 'framer-motion'
import { useEffect } from 'react'
import { animations, LottieAnimation } from '@/shared/ui/lottie'
import { usePendingClose } from '../model/pending-close'

const ERROR_VISIBLE_MS = 5000

export function CloseUndoToast() {
  const { ticketId, error, cancel, fail } = usePendingClose()

  useEffect(() => {
    if (!error) {
      return
    }
    const timer = setTimeout(() => fail(null), ERROR_VISIBLE_MS)
    return () => clearTimeout(timer)
  }, [error, fail])

  return (
    <AnimatePresence>
      {(ticketId !== null || error) && (
        <motion.div
          role="status"
          className="fixed bottom-24 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-2xl border border-line bg-card py-2 pr-2 pl-3 text-sm"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
        >
          {error ? (
            <span className="px-1 text-negative">{error}</span>
          ) : (
            <>
              <LottieAnimation src={animations.closed} speed={1.2} className="-m-1 size-7" />
              <span>Обращение №{ticketId} закрыто</span>
              <button
                type="button"
                onClick={cancel}
                className="rounded-full px-3 py-1.5 font-medium text-brand hover:bg-hover"
              >
                Отменить
              </button>
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
