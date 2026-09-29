import { motion, useReducedMotion } from 'framer-motion'
import { sparklinePath } from '../lib/sparkline'

const WIDTH = 96
const HEIGHT = 32

// The period's days at a glance, next to the total; plain SVG, no chart library.
export function Sparkline({ values, color }: { values: number[]; color: string }) {
  const reduceMotion = useReducedMotion()
  const path = sparklinePath(values, WIDTH, HEIGHT)
  if (!path) {
    return null
  }
  return (
    <svg
      viewBox={`-1 -2 ${WIDTH + 2} ${HEIGHT + 4}`}
      className="h-8 w-24 shrink-0 overflow-visible"
      aria-hidden="true"
    >
      <path d={`${path} L${WIDTH},${HEIGHT} L0,${HEIGHT} Z`} fill={color} fillOpacity={0.1} />
      <motion.path
        key={path}
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
        initial={reduceMotion ? false : { pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      />
    </svg>
  )
}
