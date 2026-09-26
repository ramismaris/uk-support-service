import { Button } from '@maxhub/max-ui'
import { useState } from 'react'
import type { TicketDetail, TicketStatus } from '@/entities/ticket'
import { primaryStatusAction, statusActionLabel } from '../lib/status-actions'
import { useChangeStatus } from '../model/use-change-status'
import { useCloseWithUndo } from '../model/use-close-with-undo'
import { usePendingClose } from '../model/pending-close'
import { ActionsMenu } from './ActionsMenu'
import { RejectDialog } from './RejectDialog'

// One primary next step in the chat header; everything else behind "⋯".
export function StatusActions({ ticket }: { ticket: TicketDetail }) {
  const change = useChangeStatus(ticket.id)
  const closeWithUndo = useCloseWithUndo(ticket.id)
  const closing = usePendingClose((state) => state.ticketId === ticket.id)
  const [rejecting, setRejecting] = useState(false)

  const run = (status: TicketStatus) => {
    if (status === 'REJECTED') {
      setRejecting(true)
    } else if (status === 'CLOSED') {
      closeWithUndo()
    } else {
      change.mutate({ status, comment: null })
    }
  }

  const primary = primaryStatusAction(ticket.status, ticket.allowed_statuses)
  const secondary = ticket.allowed_statuses.filter((status) => status !== primary)
  const busy = change.isPending || closing

  return (
    <div className="relative flex shrink-0 items-center gap-1">
      {primary && (
        <Button size="small" disabled={busy} onClick={() => run(primary)}>
          {statusActionLabel(ticket.status, primary)}
        </Button>
      )}
      <ActionsMenu
        disabled={busy}
        actions={secondary.map((status) => ({
          key: status,
          label: statusActionLabel(ticket.status, status),
          destructive: status === 'REJECTED',
          onSelect: () => run(status),
        }))}
      />
      {change.error && !rejecting && (
        <p
          role="alert"
          className="absolute top-full right-0 z-20 mt-1 max-w-72 rounded-xl border border-line bg-card px-3 py-2 text-sm text-negative"
        >
          {change.error.message}
        </p>
      )}
      <RejectDialog
        open={rejecting}
        pending={change.isPending}
        serverError={change.error?.message}
        onClose={() => setRejecting(false)}
        onConfirm={(reason) =>
          change.mutate(
            { status: 'REJECTED', comment: reason },
            { onSuccess: () => setRejecting(false) },
          )
        }
      />
    </div>
  )
}
