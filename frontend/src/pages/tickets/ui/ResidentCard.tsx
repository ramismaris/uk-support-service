import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, Phone, Star } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { isPhoto } from '@/entities/message'
import { ticketTypeLabels, type TicketDetail } from '@/entities/ticket'
import { PhotoViewer } from './PhotoViewer'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3 text-sm">
      <span className="w-28 shrink-0 text-fg-3">{label}</span>
      <span className="min-w-0 flex-1">{children}</span>
    </div>
  )
}

function resident(ticket: TicketDetail) {
  return {
    name: [ticket.client.first_name, ticket.client.last_name].filter(Boolean).join(' '),
    address: ticket.building
      ? `${ticket.building.address}${ticket.apartment ? `, кв. ${ticket.apartment}` : ''}`
      : null,
  }
}

// Photos from the request form: a grid of square previews, opened in the chat's photo viewer.
function TicketPhotos({ ticket }: { ticket: TicketDetail }) {
  const [viewerIndex, setViewerIndex] = useState<number | null>(null)
  const author = resident(ticket).name
  const photos = ticket.files
    .filter(isPhoto)
    .map((file) => ({ file, author, sentAt: ticket.created_at }))

  return (
    <>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(4.5rem,1fr))] gap-1.5 pt-1">
        {photos.map((photo, index) => (
          <button
            key={photo.file.id}
            type="button"
            aria-label={`Открыть фото ${index + 1} из ${photos.length}`}
            className="aspect-square overflow-hidden rounded-lg bg-press transition-opacity hover:opacity-85"
            onClick={() => setViewerIndex(index)}
          >
            <img src={photo.file.url} alt="" loading="lazy" className="size-full object-cover" />
          </button>
        ))}
      </div>
      <AnimatePresence>
        {viewerIndex !== null && (
          <PhotoViewer
            photos={photos}
            index={viewerIndex}
            onIndexChange={setViewerIndex}
            onClose={() => setViewerIndex(null)}
          />
        )}
      </AnimatePresence>
    </>
  )
}

function ResidentDetails({ ticket }: { ticket: TicketDetail }) {
  const phone = ticket.contact_phone
  return (
    <div className="flex flex-col gap-2">
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
      {ticket.files.length > 0 && <TicketPhotos ticket={ticket} />}
    </div>
  )
}

// Pinned above the chat like a pinned message in Max: who, where, what — details on demand.
export function ResidentCard({ ticket }: { ticket: TicketDetail }) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLElement>(null)
  const summary = useRef<HTMLParagraphElement>(null)
  // The full description goes into the details only when the one-line summary cuts it.
  const [cut, setCut] = useState(false)
  const { name, address } = resident(ticket)

  // The details drop over the chat, so a click outside or Esc puts them away.
  useEffect(() => {
    if (!open) {
      return
    }
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Element
      // The photo viewer opens from the details in a portal; using it keeps them open.
      if (!root.current?.contains(target) && !target.closest('[role="dialog"]')) {
        setOpen(false)
      }
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !document.querySelector('[role="dialog"]')) {
        setOpen(false)
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <section ref={root} className="relative z-20 border-b border-line bg-layer 3xl:hidden">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => {
          const element = summary.current
          setCut(element !== null && element.scrollHeight > element.clientHeight)
          setOpen(!open)
        }}
        className="flex w-full items-start gap-3 px-4 py-2.5 text-left"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
            <span className="font-medium">{name}</span>
            {address && <span className="text-fg-2">{address}</span>}
          </div>
          <p ref={summary} className="mt-0.5 line-clamp-1 text-sm text-fg-2">
            {ticket.description}
          </p>
        </div>
        <ChevronDown
          size={18}
          strokeWidth={2}
          className={`mt-0.5 shrink-0 text-fg-3 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Over the chat, not in the flow: opening the details does not push the messages. */}
      <AnimatePresence>
        {open && (
          <motion.div
            className="absolute inset-x-0 top-full flex max-h-[60dvh] flex-col gap-3 overflow-y-auto border-b border-line bg-layer px-4 pt-1 pb-4 shadow-lg"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
          >
            {cut && <p className="text-sm break-words whitespace-pre-wrap">{ticket.description}</p>}
            <ResidentDetails ticket={ticket} />
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}

// Wide monitors: the same details as a column beside the chat, always open.
export function ResidentPanel({ ticket }: { ticket: TicketDetail }) {
  const { name, address } = resident(ticket)
  return (
    <aside className="hidden w-96 shrink-0 flex-col gap-4 overflow-y-auto border-l border-line bg-layer p-5 3xl:flex">
      <div>
        <h2 className="text-lg font-semibold">{name}</h2>
        {address && <p className="text-sm text-fg-2">{address}</p>}
      </div>
      <p className="text-sm break-words whitespace-pre-wrap">{ticket.description}</p>
      <ResidentDetails ticket={ticket} />
    </aside>
  )
}
