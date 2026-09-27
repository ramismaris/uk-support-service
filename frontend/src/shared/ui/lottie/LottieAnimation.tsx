import type { DotLottie } from '@lottiefiles/dotlottie-react'
import wasmUrl from '@lottiefiles/dotlottie-web/dotlottie-player.wasm?url'
import { useReducedMotion } from 'framer-motion'
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { recolorLottie } from '@/shared/lib/color'
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
  // Called exactly once: when playback ends, or by a fallback timer if it never does.
  onComplete?: () => void
  // Repaints strokes and fills in this colour (the company's brand colour).
  tint?: string
}

type Tinted = { key: string; data: string } | { key: string; failed: true }

export function LottieAnimation({
  src,
  className,
  speed = 1,
  onComplete,
  tint,
}: LottieAnimationProps) {
  // Reduced motion: the player shows the first frame and does not play.
  const reduced = useReducedMotion() ?? false
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

  const tintKey = tint ? `${src}|${tint}` : null
  const [tinted, setTinted] = useState<Tinted | null>(null)
  useEffect(() => {
    if (!tint || !tintKey) {
      return
    }
    let cancelled = false
    fetch(src)
      .then((response) => response.json())
      .then((json: unknown) => {
        if (!cancelled) {
          setTinted({ key: tintKey, data: JSON.stringify(recolorLottie(json, tint)) })
        }
      })
      // The original colours are better than no animation.
      .catch(() => !cancelled && setTinted({ key: tintKey, failed: true }))
    return () => {
      cancelled = true
    }
  }, [src, tint, tintKey])

  const current = tinted && tinted.key === tintKey ? tinted : null
  if (tintKey && !current) {
    return <div className={className} />
  }
  const source = current && 'data' in current ? { data: current.data } : { src }

  const attach = (player: DotLottie | null) => {
    if (!player) {
      return
    }
    player.addEventListener('complete', () => completeRef.current())
  }

  return (
    <Suspense fallback={<div className={className} />}>
      <DotLottieReact
        key={tintKey ?? src}
        {...source}
        autoplay={!reduced}
        speed={speed}
        className={className}
        dotLottieRefCallback={attach}
      />
    </Suspense>
  )
}
