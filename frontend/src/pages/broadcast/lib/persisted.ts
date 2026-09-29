import type { ImageValue } from '@/features/upload-image'
import type { DraftEnvelope } from '@/shared/lib/drafts'
import type { Draft } from './validate'

export interface BroadcastDraftState {
  draft: Draft
  photo: ImageValue | null
}

// The photo's link is signed for an hour: an older draft keeps its text but not the picture.
export const PHOTO_FRESH_MS = 50 * 60 * 1000

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

function parsePhoto(raw: unknown): ImageValue | null | undefined {
  if (raw === null) {
    return null
  }
  if (isRecord(raw) && typeof raw.id === 'number' && typeof raw.url === 'string') {
    return { id: raw.id, url: raw.url }
  }
  return undefined
}

export function parseBroadcastDraft(raw: unknown): BroadcastDraftState | null {
  if (!isRecord(raw) || !isRecord(raw.draft)) {
    return null
  }
  const { text, scope, buildingIds } = raw.draft
  const photo = parsePhoto(raw.photo)
  if (
    typeof text !== 'string' ||
    (scope !== 'all' && scope !== 'selected') ||
    !Array.isArray(buildingIds) ||
    !buildingIds.every((id) => typeof id === 'number') ||
    photo === undefined
  ) {
    return null
  }
  return { draft: { text, scope, buildingIds }, photo }
}

export function restoreBroadcast(
  envelope: DraftEnvelope<BroadcastDraftState>,
  now = Date.now(),
): BroadcastDraftState {
  const stale = now - envelope.savedAt > PHOTO_FRESH_MS
  return stale ? { ...envelope.data, photo: null } : envelope.data
}

export function isBroadcastEmpty({ draft, photo }: BroadcastDraftState): boolean {
  return (
    draft.text.trim() === '' &&
    photo === null &&
    draft.scope === 'all' &&
    draft.buildingIds.length === 0
  )
}
