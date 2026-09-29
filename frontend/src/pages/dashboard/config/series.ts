// Fixed order and colours: "created" is always the brand colour, "closed" always the green of done.
export const SERIES = [
  { key: 'created', label: 'Поступило', color: 'var(--brand)' },
  { key: 'closed', label: 'Закрыто', color: 'var(--icon-positive)' },
] as const
