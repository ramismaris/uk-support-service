import { describe, expect, it } from 'vitest'
import {
  isBroadcastEmpty,
  parseBroadcastDraft,
  PHOTO_FRESH_MS,
  restoreBroadcast,
  type BroadcastDraftState,
} from './persisted'

const state = (changes: Partial<BroadcastDraftState> = {}): BroadcastDraftState => ({
  draft: { text: 'Отключение воды', scope: 'selected', buildingIds: [2, 5] },
  photo: { id: 9, url: 'https://files/9' },
  ...changes,
})

describe('parseBroadcastDraft', () => {
  it('reads what was saved', () => {
    expect(parseBroadcastDraft(JSON.parse(JSON.stringify(state())))).toEqual(state())
  })

  it('accepts a draft without a photo', () => {
    expect(parseBroadcastDraft(state({ photo: null }))).toEqual(state({ photo: null }))
  })

  it.each([
    ['not an object', 'text'],
    ['null', null],
    ['no draft', { photo: null }],
    [
      'a text that is not a string',
      { draft: { text: 5, scope: 'all', buildingIds: [] }, photo: null },
    ],
    ['an unknown scope', { draft: { text: 'а', scope: 'some', buildingIds: [] }, photo: null }],
    [
      'buildings that are not numbers',
      { draft: { text: 'а', scope: 'selected', buildingIds: ['1'] }, photo: null },
    ],
    ['a broken photo', { draft: { text: 'а', scope: 'all', buildingIds: [] }, photo: { id: 'x' } }],
  ])('rejects %s', (_name, raw) => {
    expect(parseBroadcastDraft(raw)).toBeNull()
  })
})

describe('restoreBroadcast', () => {
  const savedAt = 1_000_000

  it('keeps everything while the photo link is still valid', () => {
    expect(restoreBroadcast({ savedAt, data: state() }, savedAt + PHOTO_FRESH_MS)).toEqual(state())
  })

  it('drops a photo whose signed link has probably expired, and keeps the rest', () => {
    const restored = restoreBroadcast({ savedAt, data: state() }, savedAt + PHOTO_FRESH_MS + 1)
    expect(restored.photo).toBeNull()
    expect(restored.draft).toEqual(state().draft)
  })
})

describe('isBroadcastEmpty', () => {
  const empty = state({
    draft: { text: '', scope: 'all', buildingIds: [] },
    photo: null,
  })

  it('is empty for the form as it opens', () => {
    expect(isBroadcastEmpty(empty)).toBe(true)
  })

  it('counts spaces as no text', () => {
    expect(isBroadcastEmpty({ ...empty, draft: { ...empty.draft, text: '  \n ' } })).toBe(true)
  })

  it.each([
    ['a text', { draft: { ...empty.draft, text: 'а' } }],
    ['a photo', { photo: { id: 1, url: 'u' } }],
    [
      'chosen buildings',
      { draft: { ...empty.draft, scope: 'selected' as const, buildingIds: [1] } },
    ],
    ['the buildings mode', { draft: { ...empty.draft, scope: 'selected' as const } }],
  ])('is not empty with %s', (_name, changes) => {
    expect(isBroadcastEmpty({ ...empty, ...changes })).toBe(false)
  })
})
