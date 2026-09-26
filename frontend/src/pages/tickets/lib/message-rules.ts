export const MESSAGE_TEXT_LIMIT = 3000
const MAX_PHOTOS = 10
const MAX_FILE_SIZE = 20 * 1024 * 1024

export interface AttachmentLike {
  name: string
  type: string
  size: number
}

export function hasContent(text: string, files: unknown[]): boolean {
  return text.trim() !== '' || files.length > 0
}

// Mirrors the backend limits so the user learns about them before sending.
export function validateMessage(text: string, files: AttachmentLike[]): string | null {
  if (text.length > MESSAGE_TEXT_LIMIT) {
    return `Сообщение длиннее ${MESSAGE_TEXT_LIMIT} символов`
  }
  if (files.length > 1 && files.some((file) => !file.type.startsWith('image/'))) {
    return 'Документ отправляется один, без других файлов'
  }
  if (files.length > MAX_PHOTOS) {
    return `Можно приложить не больше ${MAX_PHOTOS} фото`
  }
  const tooBig = files.find((file) => file.size > MAX_FILE_SIZE)
  if (tooBig) {
    return `Файл «${tooBig.name}» больше 20 МБ`
  }
  return null
}
