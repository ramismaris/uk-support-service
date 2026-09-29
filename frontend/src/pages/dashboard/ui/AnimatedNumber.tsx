import { animate, useReducedMotion } from 'framer-motion'
import { useLayoutEffect, useRef } from 'react'

const DURATION = 0.6

// Written straight into the node: no re-render per frame.
export function AnimatedNumber({
  value,
  format,
}: {
  value: number
  format: (value: number) => string
}) {
  const reduceMotion = useReducedMotion()
  const node = useRef<HTMLSpanElement>(null)
  const from = useRef(0)

  useLayoutEffect(() => {
    const show = (latest: number) => {
      from.current = latest
      if (node.current) {
        node.current.textContent = format(latest)
      }
    }
    if (reduceMotion) {
      show(value)
      return
    }
    const controls = animate(from.current, value, {
      duration: DURATION,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: show,
    })
    return () => controls.stop()
  }, [value, format, reduceMotion])

  return <span ref={node} />
}
