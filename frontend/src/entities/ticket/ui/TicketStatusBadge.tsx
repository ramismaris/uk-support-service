import { CircleCheck, CircleX, Hourglass, Sparkle, Wrench, type LucideIcon } from 'lucide-react'
import { statusColors, statusLabels } from '../model/status'
import type { TicketStatus } from '../model/types'

const statusIcons: Record<TicketStatus, LucideIcon> = {
  NEW: Sparkle,
  IN_PROGRESS: Wrench,
  WAITING_CLIENT: Hourglass,
  CLOSED: CircleCheck,
  REJECTED: CircleX,
}

// Icon and colour tell the statuses apart at a glance; the label keeps it readable without colour.
export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  const Icon = statusIcons[status]
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 text-[13px] leading-4 font-medium ${statusColors[status]}`}
    >
      <Icon size={14} strokeWidth={2.25} aria-hidden="true" />
      {statusLabels[status]}
    </span>
  )
}

// The badge's icon alone, in the status colour: for counters that already carry a label.
export function TicketStatusIcon({ status, size = 14 }: { status: TicketStatus; size?: number }) {
  const Icon = statusIcons[status]
  return <Icon size={size} strokeWidth={2.25} aria-hidden="true" className={statusColors[status]} />
}
