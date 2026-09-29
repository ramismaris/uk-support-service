import { isAdmin, isStaff, type User } from '@/entities/user'
import { routePaths } from '@/shared/config'

// The admin starts from the overall picture; managers go straight to their tickets.
export function homePathFor(user: User): string {
  if (isAdmin(user)) {
    return routePaths.dashboard
  }
  return isStaff(user) ? routePaths.staff : routePaths.client
}
