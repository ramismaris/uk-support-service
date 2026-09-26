import type { DotLottie } from '@lottiefiles/dotlottie-react'
import wasmUrl from '@lottiefiles/dotlottie-web/dotlottie-player.wasm?url'
import { useReducedMotion } from 'framer-motion'
import { lazy, Suspense, useEffect, useRef } from 'react'
import { completionFallbackDelay, once } from './completion'

// Serve the player's wasm from our own build: by default it loads from a public CDN.
const DotLottieReact = lazy(() =>
  import('@lottiefiles/dotlottie-react').then((module) => {
    module.setWasmUrl(wasmUrl)
    return { default: module.DotLottieReact }
  }),
)

const COMPLETE_FALLBACK_MS = 3000

interface LottieAnimationProps {
  src: string
  className?: string
  speed?: number
  // Replays after this pause (ms); without it the animation plays once.
  repeatDelay?: number
  // Called exactly once: when playback ends, or by a fallback timer if it never does.
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
  const repeatTimer = useRef<ReturnType<typeof setTimeout>>(undefined)
  // Callers pass inline callbacks; a ref keeps one completion (and one fallback timer) per mount.
  const onCompleteRef = useRef(onComplete)
  useEffect(() => {
    onCompleteRef.current = onComplete
  })
  const completeRef = useRef<() => void>(() => {})
  const hasOnComplete = onComplete !== undefined

  useEffect(() => {
    completeRef.current = once(() => onCompleteRef.current?.())
    if (!hasOnComplete) {
      return
    }
    const fallback = setTimeout(
      () => completeRef.current(),
      completionFallbackDelay(reduced, COMPLETE_FALLBACK_MS),
    )
    return () => clearTimeout(fallback)
  }, [hasOnComplete, reduced])

  useEffect(() => () => clearTimeout(repeatTimer.current), [])

  const attach = (player: DotLottie | null) => {
    if (!player) {
      return
    }
    player.addEventListener('complete', () => {
      completeRef.current()
      if (repeatDelay !== undefined) {
        clearTimeout(repeatTimer.current)
        repeatTimer.current = setTimeout(() => {
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
