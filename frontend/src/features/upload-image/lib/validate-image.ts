const ALLOWED = ['image/jpeg', 'image/png']
const MAX_SIZE = 20 * 1024 * 1024

// The backend accepts only JPEG and PNG for content images (checked by content, not by name).
export function validateImage(file: { type: string; size: number }): string | null {
  if (!ALLOWED.includes(file.type)) {
    return 'Только JPEG или PNG'
  }
  if (file.size > MAX_SIZE) {
    return 'Файл больше 20 МБ'
  }
  return null
}
