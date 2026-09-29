import { Star } from 'lucide-react'

const MAX = 5

// Five stars filled up to the rating, fractions included (4.3 fills the fifth star by 30%).
export function Stars({ rating }: { rating: number }) {
  return (
    <span className="flex gap-0.5" aria-hidden="true">
      {Array.from({ length: MAX }, (_, index) => {
        const fill = Math.min(Math.max(rating - index, 0), 1)
        return (
          <span key={index} className="relative size-5">
            <Star size={20} strokeWidth={0} className="absolute inset-0 fill-fill" />
            <span className="absolute inset-0 overflow-hidden" style={{ width: `${fill * 100}%` }}>
              <Star size={20} strokeWidth={0} className="fill-amber-400" />
            </span>
          </span>
        )
      })}
    </span>
  )
}
