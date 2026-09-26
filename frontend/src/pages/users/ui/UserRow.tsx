import { Link, useLocation } from 'react-router'
import { roleLabels } from '@/entities/user'
import { userPath } from '@/shared/config'
import { formatRelativeTime } from '@/shared/lib/format'
import type { AdminUser } from '../api/users'
import { userName } from '../lib/names'

export function UserInitials({ user, size = 'size-9' }: { user: AdminUser; size?: string }) {
  const letters = [user.first_name, user.last_name]
    .filter((part): part is string => Boolean(part))
    .map((part) => part.charAt(0))
    .join('')
    .slice(0, 2)
    .toUpperCase()
  return (
    <span
      className={`${size} flex shrink-0 items-center justify-center rounded-full bg-fill text-sm font-medium text-fg-2`}
    >
      {letters}
    </span>
  )
}

export function UserRow({ user, active }: { user: AdminUser; active: boolean }) {
  const { search } = useLocation()
  return (
    <Link
      to={{ pathname: userPath(user.id), search }}
      aria-current={active ? 'page' : undefined}
      className={`flex items-center gap-3 border-b border-line px-3 py-3 transition-colors ${
        active ? 'bg-brand/10' : 'hover:bg-hover'
      }`}
    >
      <UserInitials user={user} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="truncate font-medium">{userName(user)}</span>
          {user.username && <span className="truncate text-sm text-fg-3">@{user.username}</span>}
        </div>
        <div className="flex items-center gap-2 text-xs text-fg-3">
          <span>{roleLabels[user.role]}</span>
          {user.is_blocked && <span className="text-negative">Заблокирован</span>}
        </div>
      </div>
      {user.last_seen_at && (
        <span className="shrink-0 text-xs text-fg-3">{formatRelativeTime(user.last_seen_at)}</span>
      )}
    </Link>
  )
}
