export const NAME_LIMIT = 64

// Category and address reach the resident as markdown, so the server rejects Max's markup.
const MARKUP = /[*_~^+`[\]#>]/

export function normalizeName(raw: string): string {
  return raw.trim().replace(/\s+/g, ' ')
}

export function validateName(raw: string): string | null {
  const name = normalizeName(raw)
  if (name === '') {
    return 'Введите название'
  }
  // The server counts characters, not UTF-16 units: an emoji is one.
  if (Array.from(name).length > NAME_LIMIT) {
    return `Не длиннее ${NAME_LIMIT} символов`
  }
  if (MARKUP.test(name)) {
    return 'Без символов разметки: * _ ~ ^ + ` [ ] # >'
  }
  return null
}
