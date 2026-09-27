export function isPhoto(file: { mime: string }): boolean {
  return file.mime.startsWith('image/')
}
