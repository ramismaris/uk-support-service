import type { components } from '@/shared/api'

type UserRole = components['schemas']['UserRole']

// An admin cannot demote or block themselves by accident; the backend refuses it too (409).
export function canEditUser(
  me: { id: number },
  user: { id: number },
): { editable: boolean; reason: string | null } {
  return me.id === user.id
    ? { editable: false, reason: 'Это вы' }
    : { editable: true, reason: null }
}

export interface ConfirmCopy {
  title: string
  text: string
  confirmLabel: string
  destructive: boolean
}

export type UserAction =
  { kind: 'block' } | { kind: 'unblock' } | { kind: 'role'; from: UserRole; to: UserRole }

export function confirmText(action: { kind: 'block' } | { kind: 'unblock' }): ConfirmCopy
export function confirmText(action: UserAction): ConfirmCopy | null
export function confirmText(action: UserAction): ConfirmCopy | null {
  switch (action.kind) {
    case 'block':
      return {
        title: 'Заблокировать пользователя?',
        text: 'Перестанет получать ответы бота и не сможет войти в панель.',
        confirmLabel: 'Заблокировать',
        destructive: true,
      }
    case 'unblock':
      return {
        title: 'Разблокировать пользователя?',
        text: 'Снова сможет писать боту и входить в панель.',
        confirmLabel: 'Разблокировать',
        destructive: false,
      }
    case 'role':
      if (action.to === 'ADMIN') {
        return {
          title: 'Сделать администратором?',
          text: 'Получит доступ к контенту бота, пользователям и оформлению.',
          confirmLabel: 'Сделать администратором',
          destructive: false,
        }
      }
      if (action.from === 'ADMIN') {
        return {
          title: 'Снять права администратора?',
          text: 'Потеряет доступ к контенту бота, пользователям и оформлению.',
          confirmLabel: 'Снять права',
          destructive: true,
        }
      }
      return null
  }
}
