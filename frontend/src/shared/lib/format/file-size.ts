const KB = 1024
const MB = 1024 * KB

const numberFormat = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 })

export function formatFileSize(bytes: number): string {
  if (bytes < KB) {
    return `${bytes} Б`
  }
  if (bytes < MB) {
    return `${numberFormat.format(bytes / KB)} КБ`
  }
  return `${numberFormat.format(bytes / MB)} МБ`
}
