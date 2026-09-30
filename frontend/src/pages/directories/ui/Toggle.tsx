interface ToggleProps {
  checked: boolean
  label: string
  disabled?: boolean
  title?: string
  onChange: (checked: boolean) => void
}

export function Toggle({ checked, label, disabled = false, title, onChange }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      title={title}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-10 shrink-0 rounded-full transition-colors focus-visible:ring-2 focus-visible:ring-brand/40 focus-visible:ring-offset-2 focus-visible:ring-offset-layer disabled:opacity-40 ${
        checked ? 'bg-brand' : 'bg-fg-3/40'
      }`}
    >
      <span
        aria-hidden="true"
        className={`absolute top-0.5 left-0.5 size-5 rounded-full bg-white shadow-sm transition-transform motion-reduce:transition-none ${
          checked ? 'translate-x-4' : ''
        }`}
      />
    </button>
  )
}
