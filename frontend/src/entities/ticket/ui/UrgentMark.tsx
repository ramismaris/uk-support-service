import { Siren } from 'lucide-react'

export function UrgentMark() {
  return (
    <span
      className="inline-flex text-red-600 dark:text-red-400"
      title="Срочное"
      aria-label="Срочное"
    >
      <Siren size={16} strokeWidth={2} />
    </span>
  )
}
