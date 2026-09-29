export const SERIES = [
  { key: 'created', label: 'Поступило' },
  { key: 'closed', label: 'Закрыто' },
] as const

export type SeriesKey = (typeof SERIES)[number]['key']
