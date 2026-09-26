import { api, unwrap } from '@/shared/api'
import type { Drafts, Section } from '../lib/sections'

export function fetchContent() {
  return unwrap(api.GET('/api/v1/admin/content'))
}

export async function saveSection<S extends Section>(section: S, draft: Drafts[S]): Promise<void> {
  const text = draft.text.trim()
  switch (section) {
    case 'welcome': {
      const welcome = draft as Drafts['welcome']
      await unwrap(
        api.PUT('/api/v1/admin/content/welcome', {
          body: { text, file_id: welcome.photo!.id },
        }),
      )
      return
    }
    case 'emergency':
      await unwrap(api.PUT('/api/v1/admin/content/emergency', { body: { text } }))
      return
    case 'services':
      await unwrap(api.PUT('/api/v1/admin/content/services', { body: { text } }))
      return
    case 'payment': {
      const payment = draft as Drafts['payment']
      await unwrap(
        api.PUT('/api/v1/admin/content/payment', {
          body: { text, url: payment.url.trim(), button_text: payment.buttonText.trim() },
        }),
      )
      return
    }
    case 'contacts': {
      const contacts = draft as Drafts['contacts']
      await unwrap(
        api.PUT('/api/v1/admin/content/contacts', {
          body: {
            text,
            phones: contacts.phones.map((phone) => ({
              title: phone.title.trim(),
              phone: phone.phone.trim(),
            })),
          },
        }),
      )
    }
  }
}
