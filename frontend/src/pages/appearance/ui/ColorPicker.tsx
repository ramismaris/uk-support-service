import { useEffect, useRef, useState } from 'react'
import { HexColorPicker } from 'react-colorful'

// Shown when the typed value is not a colour yet, so the picker still has a starting point.
const FALLBACK = '#1e88e5'

// The swatch opens a picker (saturation area and hue strip) under it; the preview follows live.
export function ColorPicker({
  value,
  valid,
  onChange,
}: {
  value: string
  valid: boolean
  onChange: (hex: string) => void
}) {
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

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-label="Выбрать свой цвет"
        aria-expanded={open}
        className="size-9 shrink-0 rounded-xl border border-line transition-transform hover:scale-105"
        style={{ backgroundColor: valid ? value : 'transparent' }}
        onClick={() => setOpen(!open)}
      />
      {open && (
        <div className="absolute top-11 left-0 z-20 rounded-2xl bg-layer p-3 shadow-lg ring-1 ring-line [&_.react-colorful]:h-44 [&_.react-colorful]:w-56 [&_.react-colorful__hue]:mt-3 [&_.react-colorful__hue]:h-4 [&_.react-colorful__hue]:rounded-full [&_.react-colorful__pointer]:size-5 [&_.react-colorful__saturation]:rounded-xl [&_.react-colorful__saturation]:border-b-0">
          <HexColorPicker color={valid ? value : FALLBACK} onChange={onChange} />
        </div>
      )}
    </div>
  )
}
