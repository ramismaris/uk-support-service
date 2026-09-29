export function composerDraftKey(ticketId: number): string {
  return `composer:${ticketId}`
}

export function parseComposerText(raw: unknown): string | null {
  return typeof raw === 'string' ? raw : null
}
