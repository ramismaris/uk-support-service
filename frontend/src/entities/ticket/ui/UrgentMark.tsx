import { Siren } from 'lucide-react'

export function UrgentMark() {
  return (
    <span className="inline-flex text-negative" title="Срочное" aria-label="Срочное">
      <Siren size={16} strokeWidth={2} />
    </span>
  )
}
