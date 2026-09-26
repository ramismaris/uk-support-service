import { api, unwrap } from '@/shared/api'

export function uploadImage(file: File) {
  const form = new FormData()
  form.append('file', file)
  return unwrap(
    api.POST('/api/v1/admin/content/images', {
      // The schema types the file as a string; the real body is the FormData.
      body: {} as never,
      bodySerializer: () => form,
    }),
  )
}
