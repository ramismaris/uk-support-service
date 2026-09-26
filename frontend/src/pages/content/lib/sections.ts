import type { components } from '@/shared/api'

export const SECTIONS = ['welcome', 'emergency', 'services', 'payment', 'contacts'] as const
export type Section = (typeof SECTIONS)[number]

export const sectionTitles: Record<Section, string> = {
  welcome: 'Приветствие',
  emergency: 'Аварийные службы',
  services: 'Услуги УК',
  payment: 'Оплата ЖКХ',
  contacts: 'Контакты',
}

export interface Photo {
  id: number
  url: string
}

export interface ContactPhone {
  title: string
  phone: string
}

export interface Drafts {
  welcome: { text: string; photo: Photo | null }
  emergency: { text: string }
  services: { text: string }
  payment: { text: string; url: string; buttonText: string }
  contacts: { text: string; phones: ContactPhone[] }
}

export type ContentResponse = components['schemas']['ContentResponse']

export function isSection(value: string | undefined): value is Section {
  return SECTIONS.includes(value as Section)
}

// null block — the admin has not filled the section in yet; the bot shows its default text.
export function draftsFromContent(content: ContentResponse): Drafts {
  const welcome = content.welcome
  return {
    welcome: {
      text: welcome?.text ?? '',
      photo:
        welcome?.file_id && welcome.file_url
          ? { id: welcome.file_id, url: welcome.file_url }
          : null,
    },
    emergency: { text: content.emergency?.text ?? '' },
    services: { text: content.services?.text ?? '' },
    payment: {
      text: content.payment?.text ?? '',
      url: content.payment?.url ?? '',
      buttonText: content.payment?.button_text ?? '',
    },
    contacts: {
      text: content.contacts?.text ?? '',
      phones: content.contacts?.phones.map((phone) => ({ ...phone })) ?? [],
    },
  }
}

export function isFilled(content: ContentResponse, section: Section): boolean {
  return content[section] !== null && content[section] !== undefined
}
