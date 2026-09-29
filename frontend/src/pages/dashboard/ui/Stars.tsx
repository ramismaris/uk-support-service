import { Star } from 'lucide-react'

const MAX = 5
const size = 'size-5 @sm:size-7 @xl:size-9'

export function Stars({ rating }: { rating: number }) {
  return (
    <span className="flex gap-0.5" aria-hidden="true">
      {Array.from({ length: MAX }, (_, index) => {
        const fill = Math.min(Math.max(rating - index, 0), 1)
        return (
          <span key={index} className={`relative ${size}`}>
            <Star strokeWidth={0} className={`absolute inset-0 fill-fill ${size}`} />
            <span className="absolute inset-0 overflow-hidden" style={{ width: `${fill * 100}%` }}>
              <Star strokeWidth={0} className={`fill-amber-400 ${size}`} />
            </span>
          </span>
        )
      })}
    </span>
  )
}
