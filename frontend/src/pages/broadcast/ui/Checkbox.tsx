import { Check } from 'lucide-react'
import type { ReactNode } from 'react'

interface CheckboxProps {
  checked: boolean
  onChange: () => void
  children: ReactNode
}

export function Checkbox({ checked, onChange, children }: CheckboxProps) {
  return (
    <label className="relative flex cursor-pointer items-center gap-3 rounded-lg px-2 py-1.5 text-sm leading-5 hover:bg-press">
      <input type="checkbox" checked={checked} onChange={onChange} className="peer sr-only" />
      <span
        aria-hidden="true"
        className="flex size-[18px] shrink-0 items-center justify-center rounded-md border-[1.5px] border-fg-3 text-white transition-colors peer-checked:border-brand peer-checked:bg-brand peer-focus-visible:ring-2 peer-focus-visible:ring-brand/40 peer-focus-visible:ring-offset-1 peer-focus-visible:ring-offset-fill [&>svg]:scale-0 [&>svg]:transition-transform peer-checked:[&>svg]:scale-100 motion-reduce:[&>svg]:transition-none"
      >
        <Check size={13} strokeWidth={3.5} />
      </span>
      {children}
    </label>
  )
}
