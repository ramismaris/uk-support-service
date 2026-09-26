import { isStaff, type User } from '@/entities/user'
import { routePaths } from '@/shared/config'

export function homePathFor(user: User): string {
  return isStaff(user) ? routePaths.staff : routePaths.client
}
