import { WifiOff } from 'lucide-react'
import type { ActiveTicketStatus, TicketFilters } from '@/entities/ticket'
import { useSocketStatus } from '@/shared/lib/ws'

const STATUS_OPTIONS: { value: ActiveTicketStatus | null; label: string }[] = [
  { value: null, label: 'Все' },
  { value: 'NEW', label: 'Новые' },
  { value: 'IN_PROGRESS', label: 'В работе' },
  { value: 'WAITING_CLIENT', label: 'Ждут ответа' },
]

interface TicketFiltersBarProps {
  filters: TicketFilters
  onChange: (filters: TicketFilters) => void
}

function chipClass(active: boolean): string {
  return `rounded-full px-3 py-1 text-sm transition-colors ${
    active
      ? 'bg-brand text-white'
      : 'bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700'
  }`
}

export function TicketFiltersBar({ filters, onChange }: TicketFiltersBarProps) {
  const online = useSocketStatus((state) => state.online)
  return (
    <div className="flex flex-col gap-2 border-b border-neutral-200 p-3 dark:border-neutral-800">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-lg font-semibold">Обращения</h1>
        {!online && (
          <span className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
            <WifiOff size={14} strokeWidth={2} />
            Нет связи
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {STATUS_OPTIONS.map((option) => (
          <button
            key={option.label}
            type="button"
            aria-pressed={filters.status === option.value}
            onClick={() => onChange({ ...filters, status: option.value })}
            className={chipClass(filters.status === option.value)}
          >
            {option.label}
          </button>
        ))}
        <button
          type="button"
          aria-pressed={filters.mine}
          onClick={() => onChange({ ...filters, mine: !filters.mine })}
          className={chipClass(filters.mine)}
        >
          Мои
        </button>
      </div>
    </div>
  )
}
