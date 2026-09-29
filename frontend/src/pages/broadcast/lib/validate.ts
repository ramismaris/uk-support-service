import type { BroadcastRequest } from '../api/broadcasts'

export const TEXT_LIMIT = 3000
export const BUILDINGS_LIMIT = 100

export type Scope = 'all' | 'selected'

export interface Draft {
  text: string
  scope: Scope
  buildingIds: number[]
}

export interface DraftErrors {
  text?: string
  buildings?: string
}

export function validateBroadcast(draft: Draft): DraftErrors {
  const errors: DraftErrors = {}
  if (draft.text.trim() === '') {
    errors.text = 'Заполните текст'
  } else if (draft.text.length > TEXT_LIMIT) {
    errors.text = `Не длиннее ${TEXT_LIMIT} символов`
  }
  if (draft.scope === 'selected') {
    if (draft.buildingIds.length === 0) {
      errors.buildings = 'Выберите хотя бы один дом'
    } else if (draft.buildingIds.length > BUILDINGS_LIMIT) {
      errors.buildings = `Не больше ${BUILDINGS_LIMIT} домов`
    }
  }
  return errors
}

export function toRequest(draft: Draft, fileId: number | null): BroadcastRequest {
  return {
    text: draft.text,
    file_id: fileId,
    building_ids: draft.scope === 'selected' ? draft.buildingIds : null,
  }
}
