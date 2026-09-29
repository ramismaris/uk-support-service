import { CircleCheck, LoaderCircle, TriangleAlert, type LucideIcon } from 'lucide-react'
import { formatDateTime } from '@/shared/lib/format'
import { MaxText } from '@/shared/ui/max-text'
import type { Broadcast, BroadcastStatus } from '../api/broadcasts'
import { broadcastProgress, statusLabel } from '../lib/progress'

const CHIPS: Record<BroadcastStatus, { icon: LucideIcon; style: string }> = {
  SENDING: { icon: LoaderCircle, style: 'bg-brand/10 text-brand' },
  DONE: { icon: CircleCheck, style: 'bg-positive/12 text-positive' },
  INTERRUPTED: { icon: TriangleAlert, style: 'bg-attention/15 text-attention' },
}

const SHOWN_BUILDINGS = 2

function StatusChip({ status }: { status: BroadcastStatus }) {
  const { icon: Icon, style } = CHIPS[status]
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full py-0.5 pr-2.5 pl-1.5 text-xs font-medium ${style}`}
    >
      <Icon
        size={14}
        strokeWidth={2.25}
        aria-hidden="true"
        className={status === 'SENDING' ? 'animate-spin' : ''}
      />
      {statusLabel(status)}
    </span>
  )
}

function audienceText(broadcast: Broadcast): string {
  const { buildings } = broadcast
  if (buildings.length === 0) {
    return 'Все жильцы'
  }
  const names = buildings.slice(0, SHOWN_BUILDINGS).map((building) => building.address)
  const rest = buildings.length - names.length
  return rest > 0 ? `${names.join('; ')} и ещё ${rest}` : names.join('; ')
}

function Progress({ broadcast }: { broadcast: Broadcast }) {
  const { handled } = broadcastProgress(broadcast)
  const total = broadcast.recipients_total
  const width = (count: number) => `${total > 0 ? (count / total) * 100 : 0}%`
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex h-1.5 overflow-hidden rounded-full bg-fill">
        <span
          className="bg-positive transition-[width] duration-500"
          style={{ width: width(broadcast.delivered_count) }}
        />
        <span
          className="bg-negative transition-[width] duration-500"
          style={{ width: width(broadcast.failed_count) }}
        />
      </div>
      <p className="text-xs text-fg-3">
        {broadcast.status === 'SENDING'
          ? `Отправлено ${handled} из ${total}`
          : `Доставлено ${broadcast.delivered_count} из ${total}`}
        {broadcast.failed_count > 0 && ` · не доставлено ${broadcast.failed_count}`}
      </p>
    </div>
  )
}

function Item({ broadcast }: { broadcast: Broadcast }) {
  const author = [broadcast.author.first_name, broadcast.author.last_name].filter(Boolean).join(' ')
  return (
    <li className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <StatusChip status={broadcast.status} />
        <span className="text-sm text-fg-2">{formatDateTime(broadcast.created_at)}</span>
        <span className="text-sm text-fg-3">{author}</span>
      </div>
      <div className="flex gap-3">
        {broadcast.file_url && (
          <img
            src={broadcast.file_url}
            alt=""
            className="size-14 shrink-0 rounded-lg object-cover"
          />
        )}
        <div className="flex min-w-0 flex-col gap-1">
          <MaxText text={broadcast.text} className="line-clamp-3 text-[15px] leading-5" />
          <span className="text-xs text-fg-3">{audienceText(broadcast)}</span>
        </div>
      </div>
      <Progress broadcast={broadcast} />
    </li>
  )
}

export function History({ items }: { items: Broadcast[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-fg-3">Рассылок пока не было</p>
  }
  return (
    <ul className="divide-y divide-line">
      {items.map((broadcast) => (
        <Item key={broadcast.id} broadcast={broadcast} />
      ))}
    </ul>
  )
}
