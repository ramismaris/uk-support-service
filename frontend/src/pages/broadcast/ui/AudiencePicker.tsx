import { Search } from 'lucide-react'
import { useState } from 'react'
import { filterBuildings, toggleId } from '../lib/buildings'
import type { Scope } from '../lib/validate'
import { useBuildings } from '../model/use-broadcasts'
import { Checkbox } from './Checkbox'

const LIST_ROWS = 7
const ROW_REM = 2
const PADDING_REM = 0.5

const SCOPES: { key: Scope; label: string }[] = [
  { key: 'all', label: 'Всем жильцам' },
  { key: 'selected', label: 'Жильцам выбранных домов' },
]

interface AudiencePickerProps {
  scope: Scope
  buildingIds: number[]
  error?: string
  onScope: (scope: Scope) => void
  onBuildingIds: (ids: number[]) => void
}

function BuildingList({
  buildingIds,
  onBuildingIds,
}: Pick<AudiencePickerProps, 'buildingIds' | 'onBuildingIds'>) {
  const buildings = useBuildings()
  const [query, setQuery] = useState('')

  if (buildings.isPending) {
    return <div className="h-40 animate-pulse rounded-xl bg-fill" />
  }
  if (buildings.isError) {
    return <p className="text-sm text-negative">{buildings.error.message}</p>
  }

  const shown = filterBuildings(buildings.data, query)
  const addShown = () => onBuildingIds([...new Set([...buildingIds, ...shown.map((b) => b.id)])])

  return (
    <div className="flex flex-col gap-2">
      <label className="relative">
        <Search
          size={16}
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-fg-3"
        />
        <input
          value={query}
          placeholder="Найти адрес"
          onChange={(event) => setQuery(event.target.value)}
          className="w-full rounded-xl bg-fill py-2 pr-3 pl-9 text-sm outline-none placeholder:text-fg-3 focus:ring-2 focus:ring-brand/40"
        />
      </label>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-fg-3">
        <span>
          Выбрано {buildingIds.length} из {buildings.data.length}
        </span>
        <span className="flex gap-3 font-medium">
          <button type="button" onClick={addShown} className="text-brand hover:underline">
            Выбрать найденные
          </button>
          <button
            type="button"
            onClick={() => onBuildingIds([])}
            className="text-fg-2 hover:text-fg"
          >
            Снять всё
          </button>
        </span>
      </div>
      {/* Sized by all the buildings, not the found ones: searching must not move the page. */}
      <ul
        className="overflow-y-auto rounded-xl bg-fill p-1"
        style={{
          height: `${Math.min(buildings.data.length, LIST_ROWS) * ROW_REM + PADDING_REM}rem`,
        }}
      >
        {shown.length === 0 && <li className="px-3 py-2 text-sm text-fg-3">Ничего не найдено</li>}
        {shown.map((building) => (
          <li key={building.id}>
            <Checkbox
              checked={buildingIds.includes(building.id)}
              onChange={() => onBuildingIds(toggleId(buildingIds, building.id))}
            >
              {building.address}
            </Checkbox>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function AudiencePicker({
  scope,
  buildingIds,
  error,
  onScope,
  onBuildingIds,
}: AudiencePickerProps) {
  return (
    <div className="flex flex-col gap-3">
      <span className="text-sm font-medium">Кому</span>
      <div role="radiogroup" aria-label="Кому" className="flex w-fit rounded-xl bg-fill p-0.5">
        {SCOPES.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            role="radio"
            aria-checked={key === scope}
            onClick={() => onScope(key)}
            className={`rounded-[10px] px-3 py-1.5 text-sm font-medium transition-colors ${
              key === scope ? 'bg-layer text-fg shadow-sm' : 'text-fg-2 hover:text-fg'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {scope === 'selected' && (
        <BuildingList buildingIds={buildingIds} onBuildingIds={onBuildingIds} />
      )}
      {error && <span className="text-sm text-negative">{error}</span>}
    </div>
  )
}
