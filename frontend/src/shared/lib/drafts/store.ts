export const DRAFT_TTL_MS = 7 * 24 * 60 * 60 * 1000

const PREFIX = 'draft:'

export interface DraftEnvelope<T> {
  savedAt: number
  data: T
}

export function draftKey(userId: number, form: string): string {
  return `${PREFIX}${userId}:${form}`
}

// localStorage throws in private windows and when it is full or blocked.
export function browserStorage(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

function isEnvelope(value: unknown): value is DraftEnvelope<unknown> {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as DraftEnvelope<unknown>).savedAt === 'number' &&
    'data' in value
  )
}

export function readDraft<T>(
  storage: Storage | null,
  key: string,
  parse: (raw: unknown) => T | null,
  now = Date.now(),
): DraftEnvelope<T> | null {
  if (!storage) {
    return null
  }
  try {
    const stored = storage.getItem(key)
    if (stored === null) {
      return null
    }
    const envelope: unknown = JSON.parse(stored)
    if (isEnvelope(envelope) && now - envelope.savedAt <= DRAFT_TTL_MS) {
      const data = parse(envelope.data)
      if (data !== null) {
        return { savedAt: envelope.savedAt, data }
      }
    }
    storage.removeItem(key)
    return null
  } catch {
    try {
      storage.removeItem(key)
    } catch {
      // Nothing more to do with a storage that fails on removal too.
    }
    return null
  }
}

export function writeDraft<T>(storage: Storage | null, key: string, data: T, now = Date.now()) {
  try {
    storage?.setItem(key, JSON.stringify({ savedAt: now, data } satisfies DraftEnvelope<T>))
  } catch {
    // A draft that cannot be kept is not worth an error for the person typing.
  }
}

export function clearDraft(storage: Storage | null, key: string) {
  try {
    storage?.removeItem(key)
  } catch {
    // Same as writing.
  }
}

export function clearAllDrafts(storage: Storage | null) {
  if (!storage) {
    return
  }
  try {
    const keys = Array.from({ length: storage.length }, (_, index) => storage.key(index))
    for (const key of keys) {
      if (key?.startsWith(PREFIX)) {
        storage.removeItem(key)
      }
    }
  } catch {
    // Same as writing.
  }
}
