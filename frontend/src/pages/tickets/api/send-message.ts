import { api, unwrap } from '@/shared/api'

export function sendMessage(ticketId: number, text: string, files: File[]) {
  const form = new FormData()
  const trimmed = text.trim()
  if (trimmed) {
    form.append('text', trimmed)
  }
  for (const file of files) {
    form.append('files', file)
  }
  return unwrap(
    api.POST('/api/v1/staff/tickets/{ticket_id}/messages', {
      params: { path: { ticket_id: ticketId } },
      // The schema types multipart fields as strings; the real body is the FormData.
      body: {} as never,
      bodySerializer: () => form,
    }),
  )
}
