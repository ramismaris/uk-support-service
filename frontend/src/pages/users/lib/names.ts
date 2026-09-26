import type { AdminUser } from '../api/users'

export function userName(user: AdminUser): string {
  return [user.first_name, user.last_name].filter(Boolean).join(' ')
}
