import { statusDots, statusLabels } from '../model/status'
import type { TicketStatus } from '../model/types'

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  // NEW is the one status that asks the manager to act, so only it is emphasised.
  const emphasis = status === 'NEW' ? 'font-medium text-brand' : 'text-fg-2'
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 text-[13px] leading-4 ${emphasis}`}>
      <span className={`size-1.5 rounded-full ${statusDots[status]}`} aria-hidden="true" />
      {statusLabels[status]}
    </span>
  )
}
