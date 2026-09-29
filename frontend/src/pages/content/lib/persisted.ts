import type { Drafts, Section } from './sections'

type AnyDraft = Drafts[Section]

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const isPhone = (value: unknown): value is { title: string; phone: string } =>
  isRecord(value) && typeof value.title === 'string' && typeof value.phone === 'string'

// Photos stay out of the stored draft: their signed links do not last.
export function storableDraft(draft: AnyDraft): Record<string, unknown> {
  const rest: Record<string, unknown> = { ...draft }
  delete rest.photo
  return rest
}

export function restoreSectionDraft<S extends Section>(
  section: S,
  saved: Drafts[S],
  raw: unknown,
): Drafts[S] | null {
  if (!isRecord(raw) || typeof raw.text !== 'string') {
    return null
  }
  const text = raw.text
  if (section === 'payment') {
    if (typeof raw.url !== 'string' || typeof raw.buttonText !== 'string') {
      return null
    }
    return { ...saved, text, url: raw.url, buttonText: raw.buttonText }
  }
  if (section === 'contacts') {
    if (!Array.isArray(raw.phones) || !raw.phones.every(isPhone)) {
      return null
    }
    return { ...saved, text, phones: raw.phones.map(({ title, phone }) => ({ title, phone })) }
  }
  return { ...saved, text }
}
