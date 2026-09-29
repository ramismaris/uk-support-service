import { AlarmClock, Inbox } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import {
  TicketStatusIcon,
  ticketTypeLabels,
  useTicketList,
  type ActiveTicketStatus,
} from '@/entities/ticket'
import { routePaths, ticketPath } from '@/shared/config'
import { formatRelativeTime } from '@/shared/lib/format'
import type { Dashboard } from '../api/dashboard'
import { AnimatedNumber } from './AnimatedNumber'
import { Card } from '@/shared/ui/card'

const RECENT_COUNT = 5
const count = (value: number) => String(Math.round(value))

function Counter({
  to,
  icon,
  label,
  value,
  alert = false,
}: {
  to: string
  icon: ReactNode
  label: string
  value: number
  alert?: boolean
}) {
  return (
    <Link
      to={to}
      className={`flex min-w-0 flex-col gap-1 rounded-xl px-3 py-2.5 transition-colors ${
        alert ? 'bg-negative/10 text-negative hover:bg-negative/15' : 'bg-fill hover:bg-press'
      }`}
    >
      <span className="flex items-center gap-1.5 truncate text-xs text-fg-2">
        {icon}
        {label}
      </span>
      <span className="text-2xl leading-7 font-semibold">
        <AnimatedNumber value={value} format={count} />
      </span>
    </Link>
  )
}

const statusCounter = (status: ActiveTicketStatus) => ({
  to: `${routePaths.staff}?status=${status}`,
  icon: <TicketStatusIcon status={status} size={14} />,
})

function RecentTickets() {
  const list = useTicketList({ status: null, mine: false })
  const tickets = list.data?.pages[0]?.items.slice(0, RECENT_COUNT) ?? []

  if (list.isPending) {
    return <p className="py-2 text-sm text-fg-3">Загрузка…</p>
  }
  if (tickets.length === 0) {
    return <p className="py-2 text-sm text-fg-3">Открытых обращений нет</p>
  }
  return (
    <ul className="-mx-2 flex flex-col">
      {tickets.map((ticket) => (
        <li key={ticket.id}>
          <Link
            to={ticketPath(ticket.id)}
            className="flex gap-3 rounded-xl px-2 py-2 transition-colors hover:bg-hover"
          >
            <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-fill">
              <TicketStatusIcon status={ticket.status} size={14} />
            </span>
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="flex items-baseline gap-2 text-sm">
                <span className="truncate font-medium">
                  {ticket.category?.title ?? ticketTypeLabels[ticket.type]}
                </span>
                <span className="ml-auto shrink-0 text-xs text-fg-3">
                  {formatRelativeTime(ticket.created_at)}
                </span>
              </span>
              <span className="truncate text-xs text-fg-3">
                №{ticket.id} · {ticket.description}
              </span>
            </span>
          </Link>
        </li>
      ))}
    </ul>
  )
}

export function NowPanel({ now, className = '' }: { now: Dashboard['now']; className?: string }) {
  return (
    <Card
      title="Сейчас"
      icon={Inbox}
      aside={
        <Link to={routePaths.staff} className="font-medium text-brand hover:underline">
          Все обращения
        </Link>
      }
      className={className}
      bodyClassName="gap-4"
    >
      <div className="grid grid-cols-2 gap-2">
        <Counter {...statusCounter('NEW')} label="Новые" value={now.new} />
        <Counter {...statusCounter('IN_PROGRESS')} label="В работе" value={now.in_progress} />
        <Counter
          {...statusCounter('WAITING_CLIENT')}
          label="Ждут жильца"
          value={now.waiting_client}
        />
        <Counter
          to={routePaths.staff}
          icon={<AlarmClock size={14} strokeWidth={2.25} aria-hidden="true" />}
          label="Просрочено"
          value={now.overdue}
          alert={now.overdue > 0}
        />
      </div>
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-medium text-fg-3">Свежие обращения</h3>
        <RecentTickets />
      </div>
    </Card>
  )
}
