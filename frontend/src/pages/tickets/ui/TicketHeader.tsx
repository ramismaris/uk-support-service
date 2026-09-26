import { ChevronLeft } from 'lucide-react'
import { Link, useLocation } from 'react-router'
import {
  TicketStatusBadge,
  UrgentMark,
  ticketTypeLabels,
  type TicketDetail,
} from '@/entities/ticket'
import { routePaths } from '@/shared/config'
import { StatusActions } from './StatusActions'

export function TicketHeader({ ticket }: { ticket: TicketDetail }) {
  const { search } = useLocation()
  return (
    <header className="flex items-center gap-2 border-b border-line px-3 py-2">
      <Link
        to={{ pathname: routePaths.staff, search }}
        aria-label="К списку"
        className="-ml-1 rounded-full p-1 hover:bg-hover lg:hidden"
      >
        <ChevronLeft size={20} strokeWidth={2} />
      </Link>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2">
          <span className="font-semibold">№{ticket.id}</span>
          <span className="truncate text-sm text-fg-3">
            {ticket.category?.title ?? ticketTypeLabels[ticket.type]}
          </span>
          {ticket.priority === 'URGENT' && <UrgentMark />}
        </div>
        <TicketStatusBadge status={ticket.status} />
      </div>
      <StatusActions ticket={ticket} />
    </header>
  )
}
