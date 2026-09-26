import { MoreHorizontal } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

export interface MenuAction {
  key: string
  label: string
  destructive?: boolean
  onSelect: () => void
}

export function ActionsMenu({ actions, disabled }: { actions: MenuAction[]; disabled?: boolean }) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) {
      return
    }
    const onPointerDown = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  if (actions.length === 0) {
    return null
  }

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-label="Другие действия"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen(!open)}
        className="flex size-8 items-center justify-center rounded-full text-fg-2 hover:bg-hover"
      >
        <MoreHorizontal size={20} strokeWidth={2} />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute top-full right-0 z-30 mt-1 min-w-52 overflow-hidden rounded-xl border border-line bg-card py-1"
        >
          {actions.map((action) => (
            <button
              key={action.key}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false)
                action.onSelect()
              }}
              className={`block w-full px-4 py-2.5 text-left text-sm hover:bg-hover ${
                action.destructive ? 'text-negative' : 'text-fg'
              }`}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
