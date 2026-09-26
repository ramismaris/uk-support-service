import { describe, expect, it } from 'vitest'
import type { Message } from '@/entities/message'
import type { TicketDetail } from '@/entities/ticket'
import { buildTimeline, statusEventText } from './timeline'

type Change = TicketDetail['history'][number]

const change = (overrides: Partial<Change>): Change => ({
  from_status: null,
  to_status: 'NEW',
  changed_by: null,
  comment: null,
  created_at: '2026-09-26T10:00:00Z',
  ...overrides,
})

const message = (overrides: Partial<Message>): Message => ({
  id: 1,
  ticket_id: 1000,
  sender_type: 'CLIENT',
  author: null,
  text: 'Течёт кран',
  files: [],
  created_at: '2026-09-26T10:01:00Z',
  ...overrides,
})

const anna = { id: 1, first_name: 'Анна', last_name: null }

describe('statusEventText', () => {
  it.each([
    [change({ to_status: 'NEW' }), 'Обращение создано'],
    [change({ from_status: 'NEW', to_status: 'IN_PROGRESS' }), 'Взято в работу'],
    [change({ from_status: 'IN_PROGRESS', to_status: 'WAITING_CLIENT' }), 'Запрошен ответ жильца'],
    [
      change({ from_status: 'WAITING_CLIENT', to_status: 'IN_PROGRESS' }),
      'Жилец ответил — снова в работе',
    ],
    [change({ from_status: 'CLOSED', to_status: 'IN_PROGRESS' }), 'Переоткрыто'],
    [change({ from_status: 'IN_PROGRESS', to_status: 'CLOSED' }), 'Закрыто'],
    [change({ from_status: 'NEW', to_status: 'REJECTED' }), 'Отклонено'],
  ])('%j → %s', (input, text) => {
    expect(statusEventText(input)).toBe(text)
  })
})

describe('buildTimeline', () => {
  it('merges messages and status events in time order', () => {
    const items = buildTimeline(
      [message({ id: 1, created_at: '2026-09-26T10:01:00Z' })],
      [
        change({ to_status: 'NEW', created_at: '2026-09-26T10:00:00Z' }),
        change({
          from_status: 'NEW',
          to_status: 'IN_PROGRESS',
          changed_by: anna,
          created_at: '2026-09-26T10:05:00Z',
        }),
      ],
    )
    expect(items.map((item) => item.kind)).toEqual(['event', 'message', 'event'])
    expect(items[2]).toMatchObject({ kind: 'event', text: 'Взято в работу', actor: 'Анна' })
  })

  it('drops bot status notifications that the events already show', () => {
    const items = buildTimeline(
      [
        message({ id: 1, sender_type: 'SYSTEM', text: '🟢 Статус заявки №1000: В работе.' }),
        message({ id: 2, sender_type: 'SYSTEM', text: 'Телефон аварийной службы: 112' }),
      ],
      [],
    )
    expect(items).toHaveLength(1)
    expect(items[0]).toMatchObject({ kind: 'message' })
  })

  it('keeps the rejection reason on the event', () => {
    const [item] = buildTimeline(
      [],
      [change({ from_status: 'NEW', to_status: 'REJECTED', comment: 'Не наш дом' })],
    )
    expect(item).toMatchObject({ kind: 'event', text: 'Отклонено', comment: 'Не наш дом' })
  })
})
