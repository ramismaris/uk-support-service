import { Check, ChevronDown, ChevronUp, Pencil, X } from 'lucide-react'
import { useState, type KeyboardEvent } from 'react'
import type { DirectoryItem } from '../api/directories'
import { normalizeName, validateName } from '../lib/name'
import { Toggle } from './Toggle'

interface DirectoryRowProps {
  item: DirectoryItem
  // Enabling is blocked while 29 are already on.
  canEnable: boolean
  // Only categories have an order.
  onMove?: (delta: -1 | 1) => void
  canMoveUp?: boolean
  canMoveDown?: boolean
  onRename: (name: string) => Promise<boolean>
  onToggle: (active: boolean) => void
}

const iconButton =
  'flex size-8 items-center justify-center rounded-lg text-fg-3 transition-colors hover:bg-hover hover:text-fg disabled:opacity-30 disabled:hover:bg-transparent'

export function DirectoryRow({
  item,
  canEnable,
  onMove,
  canMoveUp = true,
  canMoveDown = true,
  onRename,
  onToggle,
}: DirectoryRowProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(item.name)
  const [error, setError] = useState<string | null>(null)

  const start = () => {
    setDraft(item.name)
    setError(null)
    setEditing(true)
  }

  const save = async () => {
    const problem = validateName(draft)
    setError(problem)
    if (problem) {
      return
    }
    if (normalizeName(draft) === item.name) {
      setEditing(false)
      return
    }
    if (await onRename(normalizeName(draft))) {
      setEditing(false)
    }
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      void save()
    } else if (event.key === 'Escape') {
      setEditing(false)
    }
  }

  if (editing) {
    return (
      <li className="flex flex-col gap-1 py-2">
        <div className="flex items-center gap-1">
          <input
            autoFocus
            value={draft}
            aria-label="Название"
            aria-invalid={error ? true : undefined}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            className="min-w-0 flex-1 rounded-lg bg-fill px-3 py-1.5 text-[15px] outline-none focus:ring-2 focus:ring-brand/40"
          />
          <button
            type="button"
            aria-label="Сохранить"
            onClick={() => void save()}
            className={iconButton}
          >
            <Check size={18} strokeWidth={2.25} />
          </button>
          <button
            type="button"
            aria-label="Отмена"
            onClick={() => setEditing(false)}
            className={iconButton}
          >
            <X size={18} strokeWidth={2.25} />
          </button>
        </div>
        {error && <span className="text-sm text-negative">{error}</span>}
      </li>
    )
  }

  return (
    <li className="flex items-center gap-1 py-1.5">
      <span
        className={`min-w-0 flex-1 truncate text-[15px] ${item.active ? '' : 'text-fg-3'}`}
        title={item.name}
      >
        {item.name}
      </span>
      {!item.active && <span className="mr-1 shrink-0 text-xs text-fg-3">отключён</span>}
      {onMove && (
        <>
          <button
            type="button"
            aria-label="Выше"
            disabled={!canMoveUp}
            onClick={() => onMove(-1)}
            className={iconButton}
          >
            <ChevronUp size={18} strokeWidth={2.25} />
          </button>
          <button
            type="button"
            aria-label="Ниже"
            disabled={!canMoveDown}
            onClick={() => onMove(1)}
            className={iconButton}
          >
            <ChevronDown size={18} strokeWidth={2.25} />
          </button>
        </>
      )}
      <button type="button" aria-label="Переименовать" onClick={start} className={iconButton}>
        <Pencil size={16} strokeWidth={2} />
      </button>
      <Toggle
        checked={item.active}
        label={item.active ? 'Отключить' : 'Включить'}
        disabled={!item.active && !canEnable}
        title={!item.active && !canEnable ? 'Уже включено 29 — отключите что-нибудь' : undefined}
        onChange={onToggle}
      />
    </li>
  )
}
