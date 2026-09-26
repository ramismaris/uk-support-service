import { Button } from '@maxhub/max-ui'
import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
import type { TicketDetail, TicketStatus } from '@/entities/ticket'
import { animations, LottieAnimation } from '@/shared/ui/lottie'
import { statusActionLabel } from '../lib/status-actions'
import { useChangeStatus } from '../model/use-change-status'
import { RejectDialog } from './RejectDialog'

const CLOSED_HOLD = 400

function ClosedCelebration({ onDone }: { onDone: () => void }) {
  return (
    <motion.div
      className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-white/60 backdrop-blur-sm dark:bg-neutral-950/60"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="flex flex-col items-center gap-2 rounded-2xl bg-white px-6 py-4 shadow-lg dark:bg-neutral-900">
        <LottieAnimation
          src={animations.closed}
          speed={1.2}
          className="size-24"
          onComplete={() => setTimeout(onDone, CLOSED_HOLD)}
        />
        <span className="text-sm font-medium">Обращение закрыто</span>
      </div>
    </motion.div>
  )
}

export function StatusActions({ ticket }: { ticket: TicketDetail }) {
  const change = useChangeStatus(ticket.id)
  const [rejecting, setRejecting] = useState(false)
  const [justClosed, setJustClosed] = useState(false)

  const run = (status: TicketStatus) => {
    if (status === 'REJECTED') {
      setRejecting(true)
      return
    }
    change.mutate(
      { status, comment: null },
      { onSuccess: () => setJustClosed(status === 'CLOSED') },
    )
  }

  return (
    <>
      {/* Outside the buttons: after closing, a manager has no actions left but still sees this. */}
      <AnimatePresence>
        {justClosed && <ClosedCelebration onDone={() => setJustClosed(false)} />}
      </AnimatePresence>
      {ticket.allowed_statuses.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap gap-2">
            {ticket.allowed_statuses.map((status) => (
              <Button
                key={status}
                size="small"
                variant={status === 'REJECTED' ? 'secondary' : 'primary'}
                disabled={change.isPending}
                onClick={() => run(status)}
              >
                {statusActionLabel(ticket.status, status)}
              </Button>
            ))}
          </div>
          {change.error && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              {change.error.message}
            </p>
          )}
          <RejectDialog
            open={rejecting}
            pending={change.isPending}
            onClose={() => setRejecting(false)}
            onConfirm={(reason) =>
              change.mutate(
                { status: 'REJECTED', comment: reason },
                { onSuccess: () => setRejecting(false) },
              )
            }
          />
        </div>
      )}
    </>
  )
}
