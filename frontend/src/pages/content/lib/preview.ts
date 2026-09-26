import type { Drafts, Section } from './sections'

export interface PreviewButton {
  label: string
  url?: string
}

export interface BotPreview {
  photoUrl: string | null
  text: string
  buttons: PreviewButton[]
}

// Mirrors backend/src/bot/handlers/menu.py and keyboards.py.
const MAIN_MENU = [
  'Подать заявку',
  'Мои заявки',
  'Аварийные службы',
  'Услуги УК',
  'Оплата ЖКХ',
  'Задать вопрос',
]
const BACK: PreviewButton = { label: '« В меню' }

export function botPreview<S extends Section>(section: S, draft: Drafts[S]): BotPreview {
  switch (section) {
    case 'welcome': {
      const welcome = draft as Drafts['welcome']
      return {
        photoUrl: welcome.photo?.url ?? null,
        text: welcome.text,
        buttons: MAIN_MENU.map((label) => ({ label })),
      }
    }
    case 'payment': {
      const payment = draft as Drafts['payment']
      return {
        photoUrl: null,
        text: payment.text,
        buttons: [{ label: payment.buttonText, url: payment.url }, BACK],
      }
    }
    case 'contacts': {
      const contacts = draft as Drafts['contacts']
      const lines = [contacts.text]
      if (contacts.phones.length > 0) {
        lines.push('', ...contacts.phones.map((phone) => `${phone.title}: ${phone.phone}`))
      }
      return {
        photoUrl: null,
        text: lines.join('\n'),
        buttons: [{ label: 'Написать вопрос' }, BACK],
      }
    }
    default:
      return { photoUrl: null, text: draft.text, buttons: [BACK] }
  }
}
