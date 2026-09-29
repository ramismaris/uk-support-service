import { AlarmClock } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { TicketStatusIcon, type ActiveTicketStatus } from '@/entities/ticket'
import { routePaths } from '@/shared/config'
import type { Dashboard } from '../api/dashboard'
import { AnimatedNumber } from './AnimatedNumber'

const count = (value: number) => String(Math.round(value))

const tile = 'flex min-w-0 flex-col gap-2 rounded-xl p-3 transition-colors'

function TileBody({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <>
      <span className="flex items-center gap-1.5 text-sm text-fg-2">
        {icon}
        {label}
      </span>
      <span className="text-[32px] leading-9 font-semibold">
        <AnimatedNumber value={value} format={count} />
      </span>
    </>
  )
}

// Each open status leads to the ticket list filtered by it.
function StatusTile({
  status,
  label,
  value,
}: {
  status: ActiveTicketStatus
  label: string
  value: number
}) {
  return (
    <Link to={`${routePaths.staff}?status=${status}`} className={`${tile} bg-fill hover:bg-press`}>
      <TileBody icon={<TicketStatusIcon status={status} size={16} />} label={label} value={value} />
    </Link>
  )
}

export function NowStrip({ now }: { now: Dashboard['now'] }) {
  const overdue = now.overdue > 0
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      <StatusTile status="NEW" label="Новые" value={now.new} />
      <StatusTile status="IN_PROGRESS" label="В работе" value={now.in_progress} />
      <StatusTile status="WAITING_CLIENT" label="Ждут жильца" value={now.waiting_client} />
      <div className={`${tile} ${overdue ? 'bg-negative/10 text-negative' : 'bg-fill'}`}>
        <TileBody
          icon={
            <AlarmClock
              size={16}
              strokeWidth={2.25}
              aria-hidden="true"
              className={overdue ? 'text-negative' : 'text-fg-3'}
            />
          }
          label={overdue ? 'Просрочено' : 'Просрочек нет'}
          value={now.overdue}
        />
      </div>
    </div>
  )
}
