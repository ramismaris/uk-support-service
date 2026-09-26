import { Button } from '@maxhub/max-ui'
import { useState } from 'react'
import type { TicketDetail, TicketStatus } from '@/entities/ticket'
import { statusActionLabel } from '../lib/status-actions'
import { useChangeStatus } from '../model/use-change-status'
import { RejectDialog } from './RejectDialog'

export function StatusActions({ ticket }: { ticket: TicketDetail }) {
  const change = useChangeStatus(ticket.id)
  const [rejecting, setRejecting] = useState(false)

  if (ticket.allowed_statuses.length === 0) {
    return null
  }

  const run = (status: TicketStatus) => {
    if (status === 'REJECTED') {
      setRejecting(true)
      return
    }
    change.mutate({ status, comment: null })
  }

  return (
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
  )
}
