import { NavLink, useLocation } from 'react-router'
import {
  TicketStatusBadge,
  UrgentMark,
  ticketTypeLabels,
  type TicketListItem,
} from '@/entities/ticket'
import { ticketPath } from '@/shared/config'
import { formatRelativeTime } from '@/shared/lib/format'

export function TicketRow({ ticket }: { ticket: TicketListItem }) {
  const { search } = useLocation()
  const address = ticket.building
    ? `${ticket.building.address}${ticket.apartment ? `, кв. ${ticket.apartment}` : ''}`
    : null

  return (
    <NavLink
      to={{ pathname: ticketPath(ticket.id), search }}
      className={({ isActive }) =>
        `flex flex-col gap-1 border-b border-neutral-100 px-3 py-3 transition-colors dark:border-neutral-800/60 ${
          isActive ? 'bg-brand/10' : 'hover:bg-neutral-100 dark:hover:bg-neutral-900'
        }`
      }
    >
      <div className="flex items-center gap-2">
        {ticket.unread && (
          <span className="size-2 shrink-0 rounded-full bg-brand" aria-label="Непрочитано" />
        )}
        <span className="font-medium">№{ticket.id}</span>
        <span className="truncate text-sm text-neutral-500">
          {ticket.category?.title ?? ticketTypeLabels[ticket.type]}
        </span>
        {ticket.priority === 'URGENT' && <UrgentMark />}
        <span className="ml-auto shrink-0 text-xs text-neutral-500">
          {formatRelativeTime(ticket.created_at)}
        </span>
      </div>
      <p className="line-clamp-2 text-sm">{ticket.description}</p>
      <div className="flex items-center gap-2 text-xs text-neutral-500">
        <span className="truncate">
          {ticket.client.first_name}
          {address && ` · ${address}`}
        </span>
        <span className="ml-auto">
          <TicketStatusBadge status={ticket.status} />
        </span>
      </div>
    </NavLink>
  )
}
