import { ChevronLeft, PanelRight } from 'lucide-react'
import { Link, useLocation } from 'react-router'
import {
  TicketStatusBadge,
  UrgentMark,
  ticketTypeLabels,
  type TicketDetail,
} from '@/entities/ticket'
import { routePaths } from '@/shared/config'

export type TicketTab = 'chat' | 'details'

interface TicketHeaderProps {
  ticket: TicketDetail
  tab: TicketTab
  onTabChange: (tab: TicketTab) => void
  // Shown between lg and xl, where details live in a drawer.
  onOpenDetails: () => void
}

export function TicketHeader({ ticket, tab, onTabChange, onOpenDetails }: TicketHeaderProps) {
  const { search } = useLocation()
  return (
    <header className="border-b border-neutral-200 dark:border-neutral-800">
      <div className="flex items-center gap-2 px-3 py-2">
        <Link
          to={{ pathname: routePaths.staff, search }}
          aria-label="К списку"
          className="-ml-1 rounded-full p-1 hover:bg-neutral-100 lg:hidden dark:hover:bg-neutral-800"
        >
          <ChevronLeft size={20} strokeWidth={2} />
        </Link>
        <span className="font-semibold">№{ticket.id}</span>
        <span className="truncate text-sm text-neutral-500">
          {ticket.category?.title ?? ticketTypeLabels[ticket.type]}
        </span>
        {ticket.priority === 'URGENT' && <UrgentMark />}
        <span className="ml-auto">
          <TicketStatusBadge status={ticket.status} />
        </span>
        <button
          type="button"
          aria-label="Детали"
          onClick={onOpenDetails}
          className="hidden rounded-full p-1 hover:bg-neutral-100 lg:inline-flex xl:hidden dark:hover:bg-neutral-800"
        >
          <PanelRight size={20} strokeWidth={2} />
        </button>
      </div>
      <div className="flex lg:hidden" role="tablist">
        {(['chat', 'details'] as const).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={tab === value}
            onClick={() => onTabChange(value)}
            className={`flex-1 border-b-2 py-2 text-sm ${
              tab === value
                ? 'border-brand font-medium text-brand'
                : 'border-transparent text-neutral-500'
            }`}
          >
            {value === 'chat' ? 'Чат' : 'Детали'}
          </button>
        ))}
      </div>
    </header>
  )
}
