import { describe, expect, it } from 'vitest'
import { clearAllDrafts, clearDraft, DRAFT_TTL_MS, draftKey, readDraft, writeDraft } from './store'

function memoryStorage(): Storage {
  const items = new Map<string, string>()
  return {
    get length() {
      return items.size
    },
    key: (index) => [...items.keys()][index] ?? null,
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => void items.set(key, value),
    removeItem: (key) => void items.delete(key),
    clear: () => items.clear(),
  }
}

const asText = (raw: unknown) => (typeof raw === 'string' ? raw : null)
const NOW = 1_000_000

describe('draftKey', () => {
  it('separates users and forms', () => {
    expect(draftKey(7, 'broadcast')).toBe('draft:7:broadcast')
    expect(draftKey(8, 'broadcast')).not.toBe(draftKey(7, 'broadcast'))
  })
})

describe('readDraft', () => {
  it('returns what was written, with its time', () => {
    const storage = memoryStorage()
    writeDraft(storage, 'k', 'привет', NOW)
    expect(readDraft(storage, 'k', asText, NOW + 5)).toEqual({ savedAt: NOW, data: 'привет' })
  })

  it('has nothing for a key that was never written', () => {
    expect(readDraft(memoryStorage(), 'k', asText, NOW)).toBeNull()
  })

  it('drops a draft older than the time to live', () => {
    const storage = memoryStorage()
    writeDraft(storage, 'k', 'старое', NOW)
    expect(readDraft(storage, 'k', asText, NOW + DRAFT_TTL_MS)).not.toBeNull()
    expect(readDraft(storage, 'k', asText, NOW + DRAFT_TTL_MS + 1)).toBeNull()
    expect(storage.getItem('k')).toBeNull()
  })

  it('drops broken json', () => {
    const storage = memoryStorage()
    storage.setItem('k', '{oops')
    expect(readDraft(storage, 'k', asText, NOW)).toBeNull()
    expect(storage.getItem('k')).toBeNull()
  })

  it('drops data the caller does not recognise', () => {
    const storage = memoryStorage()
    writeDraft(storage, 'k', { text: 1 }, NOW)
    expect(readDraft(storage, 'k', asText, NOW)).toBeNull()
    expect(storage.getItem('k')).toBeNull()
  })

  it('drops something that is not an envelope', () => {
    const storage = memoryStorage()
    storage.setItem('k', JSON.stringify('просто строка'))
    expect(readDraft(storage, 'k', asText, NOW)).toBeNull()
  })

  it('works without a storage', () => {
    expect(readDraft(null, 'k', asText, NOW)).toBeNull()
  })
})

describe('writeDraft', () => {
  it('does not throw when the storage refuses', () => {
    const full: Storage = {
      ...memoryStorage(),
      setItem: () => {
        throw new DOMException('full', 'QuotaExceededError')
      },
    }
    expect(() => writeDraft(full, 'k', 'x', NOW)).not.toThrow()
    expect(() => writeDraft(null, 'k', 'x', NOW)).not.toThrow()
  })
})

describe('clearDraft', () => {
  it('removes one draft', () => {
    const storage = memoryStorage()
    writeDraft(storage, 'a', 'x', NOW)
    writeDraft(storage, 'b', 'y', NOW)
    clearDraft(storage, 'a')
    expect(storage.getItem('a')).toBeNull()
    expect(storage.getItem('b')).not.toBeNull()
  })
})

describe('clearAllDrafts', () => {
  it('removes every draft and leaves other keys alone', () => {
    const storage = memoryStorage()
    writeDraft(storage, draftKey(1, 'broadcast'), 'x', NOW)
    writeDraft(storage, draftKey(2, 'content:welcome'), 'y', NOW)
    storage.setItem('brand-color', '#ff0000')
    clearAllDrafts(storage)
    expect(storage.length).toBe(1)
    expect(storage.getItem('brand-color')).toBe('#ff0000')
  })
})
