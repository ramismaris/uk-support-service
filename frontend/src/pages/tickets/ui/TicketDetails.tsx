import { Star } from 'lucide-react'
import type { ReactNode } from 'react'
import { statusLabels, ticketTypeLabels, type TicketDetail } from '@/entities/ticket'
import { formatDateTime } from '@/shared/lib/format'
import { StatusActions } from './StatusActions'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-neutral-500">{label}</span>
      <span className="text-sm">{children}</span>
    </div>
  )
}

export function TicketDetails({ ticket }: { ticket: TicketDetail }) {
  const address = ticket.building
    ? `${ticket.building.address}${ticket.apartment ? `, кв. ${ticket.apartment}` : ''}`
    : null
  const clientName = [ticket.client.first_name, ticket.client.last_name].filter(Boolean).join(' ')

  return (
    <div className="flex flex-col gap-5 p-4">
      <StatusActions ticket={ticket} />

      <div className="flex flex-col gap-3">
        <Field label="Жилец">
          {clientName}
          {ticket.contact_phone && (
            <>
              {' · '}
              <a className="text-brand" href={`tel:+${ticket.contact_phone.replace(/^\+/, '')}`}>
                {ticket.contact_phone}
              </a>
            </>
          )}
        </Field>
        {address && <Field label="Адрес">{address}</Field>}
        <Field label="Тип">
          {ticketTypeLabels[ticket.type]}
          {ticket.category && ` · ${ticket.category.title}`}
        </Field>
        <Field label="Описание">
          <span className="whitespace-pre-wrap">{ticket.description}</span>
        </Field>
        {ticket.preferred_time && <Field label="Удобное время">{ticket.preferred_time}</Field>}
        <Field label="Ведёт">{ticket.assignee?.first_name ?? 'Никто'}</Field>
        {ticket.rating !== null && (
          <Field label="Оценка">
            <span className="flex gap-0.5" aria-label={`${ticket.rating} из 5`}>
              {[1, 2, 3, 4, 5].map((value) => (
                <Star
                  key={value}
                  size={16}
                  strokeWidth={2}
                  className={
                    value <= (ticket.rating ?? 0)
                      ? 'fill-amber-400 text-amber-400'
                      : 'text-neutral-300'
                  }
                />
              ))}
            </span>
          </Field>
        )}
      </div>

      {ticket.files.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {ticket.files.map((file) => (
            <a key={file.id} href={file.url} target="_blank" rel="noreferrer">
              <img
                src={file.url}
                alt={file.original_name ?? 'Фото'}
                className="aspect-square w-full rounded-lg object-cover"
                loading="lazy"
              />
            </a>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-2">
        <span className="text-xs text-neutral-500">История</span>
        <ol className="flex flex-col gap-2 text-sm">
          {ticket.history.map((change, index) => (
            <li key={index} className="flex flex-col">
              <span>
                {statusLabels[change.to_status]}
                <span className="text-neutral-500">
                  {' · '}
                  {change.changed_by?.first_name ?? 'Система'}
                  {' · '}
                  {formatDateTime(change.created_at)}
                </span>
              </span>
              {change.comment && <span className="text-neutral-500">«{change.comment}»</span>}
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
