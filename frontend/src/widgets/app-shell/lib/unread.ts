const BADGE_MAX = 99
const COUNT_PREFIX = /^\(\d+\+?\) /

export function unreadBadge(count: number): string | null {
  if (count <= 0) {
    return null
  }
  return count > BADGE_MAX ? `${BADGE_MAX}+` : String(count)
}

// "(3) УК — панель": the tab tells about new messages while the panel is in the background.
export function withUnreadCount(title: string, count: number): string {
  const base = title.replace(COUNT_PREFIX, '')
  const badge = unreadBadge(count)
  return badge ? `(${badge}) ${base}` : base
}
