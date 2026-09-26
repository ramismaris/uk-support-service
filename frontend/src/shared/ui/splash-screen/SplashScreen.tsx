import { motion } from 'framer-motion'

export function SplashScreen() {
  return (
    <div className="flex min-h-dvh items-center justify-center" aria-busy="true">
      <motion.div
        className="size-10 rounded-full border-4 border-brand/20 border-t-brand"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, rotate: 360 }}
        transition={{
          opacity: { duration: 0.3, delay: 0.2 },
          rotate: { duration: 0.9, ease: 'linear', repeat: Infinity },
        }}
        aria-label="Загрузка"
      />
    </div>
  )
}
