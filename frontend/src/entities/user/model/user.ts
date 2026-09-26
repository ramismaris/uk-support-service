import type { components } from '@/shared/api'

export type User = components['schemas']['UserResponse']
export type UserRole = User['role']

export const roleLabels: Record<UserRole, string> = {
  CLIENT: 'Жилец',
  MANAGER: 'Менеджер',
  ADMIN: 'Администратор',
}

export function isStaff(user: User): boolean {
  return user.role === 'MANAGER' || user.role === 'ADMIN'
}

export function isAdmin(user: User): boolean {
  return user.role === 'ADMIN'
}

export function isClient(user: User): boolean {
  return user.role === 'CLIENT'
}

export function getDisplayName(user: User): string {
  return [user.first_name, user.last_name].filter(Boolean).join(' ')
}
