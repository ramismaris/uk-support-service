import type { DotLottie } from '@lottiefiles/dotlottie-react'
import wasmUrl from '@lottiefiles/dotlottie-web/dotlottie-player.wasm?url'
import { useReducedMotion } from 'framer-motion'
import { lazy, Suspense, useEffect, useRef } from 'react'

// Serve the player's wasm from our own build: by default it loads from a public CDN.
const DotLottieReact = lazy(() =>
  import('@lottiefiles/dotlottie-react').then((module) => {
    module.setWasmUrl(wasmUrl)
    return { default: module.DotLottieReact }
  }),
)

interface LottieAnimationProps {
  src: string
  className?: string
  speed?: number
  // Replays after this pause (ms); without it the animation plays once.
  repeatDelay?: number
  onComplete?: () => void
}

export function LottieAnimation({
  src,
  className,
  speed = 1,
  repeatDelay,
  onComplete,
}: LottieAnimationProps) {
  // Reduced motion: the player shows the first frame and does not play.
  const reduced = useReducedMotion() ?? false
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => () => clearTimeout(timer.current), [])

  const attach = (player: DotLottie | null) => {
    if (!player) {
      return
    }
    player.addEventListener('complete', () => {
      onComplete?.()
      if (repeatDelay !== undefined) {
        timer.current = setTimeout(() => {
          player.stop()
          player.play()
        }, repeatDelay)
      }
    })
  }

  return (
    <Suspense fallback={<div className={className} />}>
      <DotLottieReact
        src={src}
        autoplay={!reduced}
        speed={speed}
        className={className}
        dotLottieRefCallback={attach}
      />
    </Suspense>
  )
}
