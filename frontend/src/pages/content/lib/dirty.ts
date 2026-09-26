// Photos compare by id: their signed urls change on every load.
function normalize(_key: string, value: unknown): unknown {
  if (value && typeof value === 'object' && 'id' in value && 'url' in value) {
    return (value as { id: unknown }).id
  }
  return value
}

// Stable identity of a draft: survives refetches that only re-sign the photo url.
export function draftSignature(draft: unknown): string {
  return JSON.stringify(draft, normalize)
}

export function isDirty(saved: unknown, draft: unknown): boolean {
  return draftSignature(saved) !== draftSignature(draft)
}
