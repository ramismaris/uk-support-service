import { WifiOff } from 'lucide-react'
import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type RefObject,
} from 'react'
import { useStaffBuildings, useStaffCategories } from '@/entities/directory'
import type { TicketFilters, TicketStatus } from '@/entities/ticket'
import { useSocketStatus } from '@/shared/lib/ws'
import { NavMenuButton } from '@/widgets/app-shell'
import { selectOptions } from '../lib/filter-options'
import { centeredScrollLeft, scrollEdges, type ScrollEdges } from '../lib/scroll-edges'
import { FilterSelect } from './FilterSelect'

const STATUS_OPTIONS: { value: TicketStatus | null; label: string }[] = [
  { value: null, label: 'Все' },
  { value: 'NEW', label: 'Новые' },
  { value: 'IN_PROGRESS', label: 'В работе' },
  { value: 'WAITING_CLIENT', label: 'Ждём жильца' },
  { value: 'CLOSED', label: 'Закрытые' },
  { value: 'REJECTED', label: 'Отклонённые' },
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

const FADE = '1.75rem'

// The chips do not all fit a phone or the narrow list: fade the edge that hides more, turn the
// mouse wheel into sideways scrolling and keep the chosen chip in view.
function useChipRow(row: RefObject<HTMLDivElement | null>, activeKey: string): CSSProperties {
  const [edges, setEdges] = useState<ScrollEdges>({ start: false, end: false })

  useLayoutEffect(() => {
    const element = row.current
    if (!element) {
      return
    }
    const update = () => setEdges(scrollEdges(element))
    const onWheel = (event: WheelEvent) => {
      const current = scrollEdges(element)
      const canMove = event.deltaY < 0 ? current.start : current.end
      if (Math.abs(event.deltaY) > Math.abs(event.deltaX) && canMove) {
        element.scrollLeft += event.deltaY
        event.preventDefault()
      }
    }
    update()
    const observer = new ResizeObserver(update)
    observer.observe(element)
    element.addEventListener('scroll', update, { passive: true })
    element.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      observer.disconnect()
      element.removeEventListener('scroll', update)
      element.removeEventListener('wheel', onWheel)
    }
  }, [row])

  // Only the row scrolls (scrollIntoView would also move its parents), and the first time at once.
  const first = useRef(true)
  useEffect(() => {
    const element = row.current
    const chip = element?.querySelector<HTMLElement>('[aria-pressed="true"]')
    if (!element || !chip) {
      return
    }
    const rowBox = element.getBoundingClientRect()
    const chipBox = chip.getBoundingClientRect()
    element.scrollTo({
      left: centeredScrollLeft({
        scrollLeft: element.scrollLeft,
        rowLeft: rowBox.left,
        rowWidth: rowBox.width,
        chipLeft: chipBox.left,
        chipWidth: chipBox.width,
      }),
      behavior: first.current ? 'auto' : 'smooth',
    })
    first.current = false
  }, [row, activeKey])

  const left = edges.start ? `transparent, black ${FADE}` : 'black, black'
  const right = edges.end ? `black calc(100% - ${FADE}), transparent` : 'black, black'
  const mask = `linear-gradient(to right, ${left}, ${right})`
  return { maskImage: mask, WebkitMaskImage: mask }
}

export function TicketFiltersBar({ filters, onChange }: TicketFiltersBarProps) {
  const online = useSocketStatus((state) => state.online)
  const chipRow = useRef<HTMLDivElement>(null)
  const chipRowStyle = useChipRow(chipRow, filters.status ?? 'ALL')
  const buildings = useStaffBuildings()
  const categories = useStaffCategories()
  const buildingOptions = selectOptions(
    (buildings.data ?? []).map((building) => ({ id: building.id, label: building.address })),
    filters.buildingId,
    'Все дома',
    (id) => `Дом №${id}`,
  )
  const categoryOptions = selectOptions(
    (categories.data ?? []).map((category) => ({ id: category.id, label: category.title })),
    filters.categoryId,
    'Все категории',
    (id) => `Категория №${id}`,
  )
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
      <div
        ref={chipRow}
        style={chipRowStyle}
        className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 whitespace-nowrap [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
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
      <div className="flex gap-2">
        <FilterSelect
          label="Дом"
          value={filters.buildingId}
          options={buildingOptions}
          onChange={(buildingId) => onChange({ ...filters, buildingId })}
        />
        <FilterSelect
          label="Категория"
          value={filters.categoryId}
          options={categoryOptions}
          onChange={(categoryId) => onChange({ ...filters, categoryId })}
        />
      </div>
    </div>
  )
}
