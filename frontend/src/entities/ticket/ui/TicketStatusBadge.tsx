import { statusLabels, statusTones } from '../model/status'
import type { TicketStatus } from '../model/types'

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusTones[status]}`}
    >
      {statusLabels[status]}
    </span>
  )
}
