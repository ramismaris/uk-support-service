import { ChevronDown, Phone, Star } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { ticketTypeLabels, type TicketDetail } from '@/entities/ticket'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3 text-sm">
      <span className="w-28 shrink-0 text-fg-3">{label}</span>
      <span className="min-w-0 flex-1">{children}</span>
    </div>
  )
}

// Pinned above the chat like a pinned message in Max: who, where, what — details on demand.
export function ResidentCard({ ticket }: { ticket: TicketDetail }) {
  const [open, setOpen] = useState(false)
  const name = [ticket.client.first_name, ticket.client.last_name].filter(Boolean).join(' ')
  const address = ticket.building
    ? `${ticket.building.address}${ticket.apartment ? `, кв. ${ticket.apartment}` : ''}`
    : null
  const phone = ticket.contact_phone

  return (
    <section className="border-b border-line bg-layer px-4 py-2.5">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex w-full items-start gap-3 text-left"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
            <span className="font-medium">{name}</span>
            {address && <span className="text-fg-2">{address}</span>}
          </div>
          <p className={`mt-0.5 text-sm text-fg-2 ${open ? '' : 'line-clamp-1'}`}>
            {ticket.description}
          </p>
        </div>
        <ChevronDown
          size={18}
          strokeWidth={2}
          className={`mt-0.5 shrink-0 text-fg-3 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="mt-3 flex flex-col gap-2 pb-1">
          {phone && (
            <Row label="Телефон">
              <a
                className="inline-flex items-center gap-1.5 text-brand"
                href={`tel:+${phone.replace(/^\+/, '')}`}
              >
                <Phone size={14} strokeWidth={2} />
                {phone}
              </a>
            </Row>
          )}
          <Row label="Тип">
            {ticketTypeLabels[ticket.type]}
            {ticket.category && ` · ${ticket.category.title}`}
          </Row>
          {ticket.preferred_time && <Row label="Удобное время">{ticket.preferred_time}</Row>}
          <Row label="Ведёт">{ticket.assignee?.first_name ?? 'Пока никто'}</Row>
          {ticket.rating !== null && (
            <Row label="Оценка">
              <span className="inline-flex gap-0.5" aria-label={`${ticket.rating} из 5`}>
                {[1, 2, 3, 4, 5].map((value) => (
                  <Star
                    key={value}
                    size={14}
                    strokeWidth={2}
                    className={
                      value <= (ticket.rating ?? 0) ? 'fill-attention text-attention' : 'text-mute'
                    }
                  />
                ))}
              </span>
            </Row>
          )}
          {ticket.files.length > 0 && (
            <div className="flex gap-2 overflow-x-auto pt-1">
              {ticket.files.map((file) => (
                <a
                  key={file.id}
                  href={file.url}
                  target="_blank"
                  rel="noreferrer"
                  className="shrink-0"
                >
                  <img
                    src={file.url}
                    alt={file.original_name ?? 'Фото'}
                    className="size-20 rounded-lg object-cover"
                    loading="lazy"
                  />
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
