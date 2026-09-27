export function isImage(file: { type: string }): boolean {
  return file.type.startsWith('image/')
}

// Title of the send dialog, as in Telegram: "Отправить 3 фото".
export function attachTitle(files: { type: string }[]): string {
  if (files.every(isImage)) {
    return files.length === 1 ? 'Отправить фото' : `Отправить ${files.length} фото`
  }
  return files.length === 1 ? 'Отправить файл' : `Отправить файлы: ${files.length}`
}

// Ctrl+V: a screenshot or a copied picture becomes an attachment; text pastes as usual.
export function pastedImages<T extends { type: string }>(files: T[]): T[] {
  return files.filter(isImage)
}
