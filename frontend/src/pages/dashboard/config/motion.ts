import type { Variants } from 'framer-motion'

// A card slides up and fades in; the page staggers them.
export const rise: Variants = {
  hidden: { opacity: 0, y: 12 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] } },
}
