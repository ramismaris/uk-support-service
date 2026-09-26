import type { Drafts, Section } from './sections'

export type FieldErrors = Record<string, string>

const TEXT_LIMIT = 3000
const BUTTON_LIMIT = 64
const LINK_LIMIT = 2048
const PHONES_LIMIT = 10
const PHONE_TITLE_LIMIT = 50
const PHONE_LIMIT = 30
const LINK = /^https?:\/\/\S+$/

function required(value: string, limit: number, empty: string): string | null {
  if (value.trim() === '') {
    return empty
  }
  return value.length > limit ? `Не длиннее ${limit} символов` : null
}

// Same limits as the backend schemas, so the admin sees problems before saving.
export function validateSection<S extends Section>(section: S, draft: Drafts[S]): FieldErrors {
  const errors: FieldErrors = {}
  const add = (field: string, error: string | null) => {
    if (error) {
      errors[field] = error
    }
  }

  add('text', required(draft.text, TEXT_LIMIT, 'Заполните текст'))

  if (section === 'welcome') {
    const welcome = draft as Drafts['welcome']
    add('photo', welcome.photo ? null : 'Добавьте фото')
  }
  if (section === 'payment') {
    const payment = draft as Drafts['payment']
    // The backend strips spaces around the link before checking it.
    const url = payment.url.trim()
    if (url.length > LINK_LIMIT) {
      add('url', `Не длиннее ${LINK_LIMIT} символов`)
    } else {
      add('url', LINK.test(url) ? null : 'Ссылка должна начинаться с http:// или https://')
    }
    add('buttonText', required(payment.buttonText, BUTTON_LIMIT, 'Заполните текст кнопки'))
  }
  if (section === 'contacts') {
    const contacts = draft as Drafts['contacts']
    if (contacts.phones.length > PHONES_LIMIT) {
      add('phones', `Не больше ${PHONES_LIMIT} телефонов`)
    }
    contacts.phones.forEach((phone, index) => {
      add(`phones.${index}.title`, required(phone.title, PHONE_TITLE_LIMIT, 'Заполните подпись'))
      add(`phones.${index}.phone`, required(phone.phone, PHONE_LIMIT, 'Заполните номер'))
    })
  }
  return errors
}
