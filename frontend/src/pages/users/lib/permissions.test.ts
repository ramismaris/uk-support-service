import { describe, expect, it } from 'vitest'
import { canEditUser, confirmText } from './permissions'

describe('canEditUser', () => {
  it('forbids changing yourself', () => {
    expect(canEditUser({ id: 1 }, { id: 1 })).toEqual({ editable: false, reason: 'Это вы' })
  })

  it('allows changing someone else', () => {
    expect(canEditUser({ id: 1 }, { id: 2 })).toEqual({ editable: true, reason: null })
  })
})

describe('confirmText', () => {
  it('explains blocking and unblocking', () => {
    expect(confirmText({ kind: 'block' })).toEqual({
      title: 'Заблокировать пользователя?',
      text: 'Перестанет получать ответы бота и не сможет войти в панель.',
      confirmLabel: 'Заблокировать',
      destructive: true,
    })
    expect(confirmText({ kind: 'unblock' }).confirmLabel).toBe('Разблокировать')
  })

  it('asks before granting or removing admin rights', () => {
    expect(confirmText({ kind: 'role', from: 'MANAGER', to: 'ADMIN' })?.title).toBe(
      'Сделать администратором?',
    )
    expect(confirmText({ kind: 'role', from: 'ADMIN', to: 'MANAGER' })?.title).toBe(
      'Снять права администратора?',
    )
  })

  it('does not ask for other role changes', () => {
    expect(confirmText({ kind: 'role', from: 'CLIENT', to: 'MANAGER' })).toBeNull()
  })
})
