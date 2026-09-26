import { describe, expect, it } from 'vitest'
import { primaryStatusAction, statusActionLabel, validateRejectReason } from './status-actions'

describe('statusActionLabel', () => {
  it.each([
    ['NEW', 'IN_PROGRESS', 'Взять в работу'],
    ['IN_PROGRESS', 'WAITING_CLIENT', 'Запросить ответ жильца'],
    ['IN_PROGRESS', 'CLOSED', 'Закрыть'],
    ['WAITING_CLIENT', 'CLOSED', 'Закрыть'],
    ['NEW', 'REJECTED', 'Отклонить'],
    ['CLOSED', 'IN_PROGRESS', 'Переоткрыть'],
    ['REJECTED', 'IN_PROGRESS', 'Переоткрыть'],
    ['WAITING_CLIENT', 'IN_PROGRESS', 'Вернуть в работу'],
  ] as const)('%s → %s: %s', (from, to, label) => {
    expect(statusActionLabel(from, to)).toBe(label)
  })
})

describe('validateRejectReason', () => {
  it('requires a reason', () => {
    expect(validateRejectReason('   ')).toBe('Укажите причину — её увидит жилец')
  })

  it('limits the length', () => {
    expect(validateRejectReason('а'.repeat(3001))).toBe('Причина длиннее 3000 символов')
  })

  it('accepts a normal reason', () => {
    expect(validateRejectReason('Не в зоне ответственности УК')).toBeNull()
  })
})

describe('primaryStatusAction', () => {
  it('suggests the natural next step', () => {
    expect(primaryStatusAction('NEW', ['IN_PROGRESS', 'REJECTED'])).toBe('IN_PROGRESS')
    expect(primaryStatusAction('IN_PROGRESS', ['WAITING_CLIENT', 'CLOSED', 'REJECTED'])).toBe(
      'CLOSED',
    )
    expect(primaryStatusAction('WAITING_CLIENT', ['IN_PROGRESS', 'CLOSED', 'REJECTED'])).toBe(
      'CLOSED',
    )
    expect(primaryStatusAction('CLOSED', ['IN_PROGRESS'])).toBe('IN_PROGRESS')
  })

  it('never makes rejection the primary action', () => {
    expect(primaryStatusAction('NEW', ['REJECTED'])).toBeNull()
  })

  it('has nothing to suggest without allowed statuses', () => {
    expect(primaryStatusAction('CLOSED', [])).toBeNull()
  })
})
