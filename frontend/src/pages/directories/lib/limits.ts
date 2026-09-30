// The bot shows one button per enabled building and category, and Max allows 29 of them.
export const ACTIVE_LIMIT = 29

export function activeCount(items: { active: boolean }[]): number {
  return items.filter((item) => item.active).length
}

export function atLimit(items: { active: boolean }[]): boolean {
  return activeCount(items) >= ACTIVE_LIMIT
}
