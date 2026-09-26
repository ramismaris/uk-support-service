export interface ThemeDraft {
  companyName: string
  primaryColor: string
}

export type ThemeErrors = Partial<Record<keyof ThemeDraft, string>>

export const NAME_LIMIT = 100
const HEX = /^#[0-9a-f]{6}$/i

// Same rules as the backend ThemeContent schema, so the admin sees problems before saving.
export function validateTheme(draft: ThemeDraft): ThemeErrors {
  const errors: ThemeErrors = {}
  const name = draft.companyName.trim()
  if (name === '') {
    errors.companyName = 'Укажите название'
  } else if (name.length > NAME_LIMIT) {
    errors.companyName = `Не длиннее ${NAME_LIMIT} символов`
  }
  if (!HEX.test(draft.primaryColor)) {
    errors.primaryColor = 'Цвет в формате #RRGGBB'
  }
  return errors
}
