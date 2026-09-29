import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

const EASE = [0.22, 1, 0.36, 1] as const

export function SplashScreen({ mark, name }: { mark: ReactNode; name: string }) {
  const reduceMotion = useReducedMotion()
  return (
    <div
      className="flex min-h-dvh flex-col items-center justify-center gap-6 p-6"
      aria-busy="true"
      aria-label="Загрузка"
    >
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: EASE }}
      >
        {mark}
      </motion.div>
      <motion.p
        className="text-center text-xl font-semibold"
        initial={reduceMotion ? false : { opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.12, ease: EASE }}
      >
        {name}
      </motion.p>
      <div className="h-1 w-28 overflow-hidden rounded-full bg-brand/15">
        {!reduceMotion && (
          <motion.span
            className="block h-full w-1/3 rounded-full bg-brand"
            initial={{ x: '-100%' }}
            animate={{ x: '300%' }}
            transition={{ duration: 1.1, ease: 'easeInOut', repeat: Infinity }}
          />
        )}
      </div>
    </div>
  )
}
