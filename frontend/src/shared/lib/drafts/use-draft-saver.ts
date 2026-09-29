import { useEffect, useRef } from 'react'
import { browserStorage, clearDraft, writeDraft } from './store'

const SAVE_DELAY_MS = 300

// Keeps the value in localStorage while it is being typed; an empty value removes the draft.
// The last keystrokes go out on pagehide, so an F5 right after typing loses nothing.
export function useDraftSaver<T>(key: string | null, value: T, isEmpty: (value: T) => boolean) {
  const latest = useRef({ key, value, isEmpty })

  useEffect(() => {
    latest.current = { key, value, isEmpty }
  })

  const persist = () => {
    const current = latest.current
    if (current.key === null) {
      return
    }
    if (current.isEmpty(current.value)) {
      clearDraft(browserStorage(), current.key)
    } else {
      writeDraft(browserStorage(), current.key, current.value)
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(persist, SAVE_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [key, value])

  useEffect(() => {
    window.addEventListener('pagehide', persist)
    return () => window.removeEventListener('pagehide', persist)
  }, [])
}
