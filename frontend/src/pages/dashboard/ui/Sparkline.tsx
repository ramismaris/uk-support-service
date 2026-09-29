import { motion, useReducedMotion } from 'framer-motion'
import { useId } from 'react'
import { sparklinePath } from '../lib/sparkline'

const WIDTH = 96
const HEIGHT = 32
// Room around the plot so the round line caps and the peak are not clipped.
const PAD = 3

export function Sparkline({ values, color }: { values: number[]; color: string }) {
  const reduceMotion = useReducedMotion()
  const clipId = `spark-${useId().replace(/:/g, '')}`
  const path = sparklinePath(values, WIDTH, HEIGHT)
  if (!path) {
    return null
  }
  return (
    <svg
      viewBox={`${-PAD} ${-PAD} ${WIDTH + PAD * 2} ${HEIGHT + PAD * 2}`}
      preserveAspectRatio="none"
      className="h-8 w-24 shrink-0 @sm:h-12 @sm:w-32 @xl:h-16 @xl:w-56"
      aria-hidden="true"
    >
      {/* Revealed left to right by a growing mask: a dashed stroke breaks with a stretched viewBox. */}
      <clipPath id={clipId}>
        <motion.rect
          key={path}
          x={-PAD}
          y={-PAD}
          height={HEIGHT + PAD * 2}
          initial={reduceMotion ? false : { width: 0 }}
          animate={{ width: WIDTH + PAD * 2 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        />
      </clipPath>
      <g clipPath={`url(#${clipId})`}>
        <path d={`${path} L${WIDTH},${HEIGHT} L0,${HEIGHT} Z`} fill={color} fillOpacity={0.1} />
        <path
          d={path}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </g>
    </svg>
  )
}
