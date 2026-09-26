import { WifiOff } from 'lucide-react'
import type { ActiveTicketStatus, TicketFilters } from '@/entities/ticket'
import { useSocketStatus } from '@/shared/lib/ws'
import { NavMenuButton } from '@/widgets/app-shell'

const STATUS_OPTIONS: { value: ActiveTicketStatus | null; label: string }[] = [
  { value: null, label: 'Все' },
  { value: 'NEW', label: 'Новые' },
  { value: 'IN_PROGRESS', label: 'В работе' },
  { value: 'WAITING_CLIENT', label: 'Ждём жильца' },
]

interface TicketFiltersBarProps {
  filters: TicketFilters
  onChange: (filters: TicketFilters) => void
}

function chipClass(active: boolean): string {
  return `rounded-full px-3 py-1 text-sm transition-colors ${
    active ? 'bg-brand/12 font-medium text-brand' : 'text-fg-2 hover:bg-hover'
  }`
}

export function TicketFiltersBar({ filters, onChange }: TicketFiltersBarProps) {
  const online = useSocketStatus((state) => state.online)
  return (
    <div className="flex flex-col gap-2 border-b border-line p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <NavMenuButton />
          <h1 className="text-lg font-semibold">Обращения</h1>
        </div>
        <div className="flex items-center gap-2">
          {!online && (
            <span className="flex items-center gap-1 text-xs text-attention">
              <WifiOff size={14} strokeWidth={2} />
              Нет связи
            </span>
          )}
          {/* A toggle, not one of the status options: it combines with any of them. */}
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
      <div className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 whitespace-nowrap [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
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
      </div>
    </div>
  )
}
