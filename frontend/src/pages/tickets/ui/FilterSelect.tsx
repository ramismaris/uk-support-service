import { ChevronDown } from 'lucide-react'
import type { SelectOption } from '../lib/filter-options'

interface FilterSelectProps {
  label: string
  value: number | null
  options: SelectOption[]
  onChange: (value: number | null) => void
}

// A native select: on a phone it opens the system picker, and it stays keyboard-friendly.
export function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  return (
    <label className="relative min-w-0 flex-1">
      <span className="sr-only">{label}</span>
      <select
        value={value ?? ''}
        onChange={(event) =>
          onChange(event.target.value === '' ? null : Number(event.target.value))
        }
        className={`w-full appearance-none truncate rounded-full py-1 pr-7 pl-3 text-sm transition-colors outline-none focus-visible:ring-2 focus-visible:ring-brand/40 ${
          value === null ? 'bg-fill text-fg-2 hover:bg-hover' : 'bg-brand/12 font-medium text-brand'
        }`}
      >
        {options.map((option) => (
          <option key={option.value ?? 'all'} value={option.value ?? ''}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown
        size={14}
        strokeWidth={2.25}
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 opacity-70"
      />
    </label>
  )
}
