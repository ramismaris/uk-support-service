import { describe, expect, it } from 'vitest'
import { statusActionLabel, validateRejectReason } from './status-actions'

describe('statusActionLabel', () => {
  it.each([
    ['NEW', 'IN_PROGRESS', 'Взять в работу'],
    ['IN_PROGRESS', 'WAITING_CLIENT', 'Нужен ответ клиента'],
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
