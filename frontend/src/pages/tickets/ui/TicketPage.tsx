import { Button } from '@maxhub/max-ui'
import { FileQuestion, SearchX } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { useTicket } from '@/entities/ticket'
import { isApiError } from '@/shared/api'
import { routePaths } from '@/shared/config'
import { EmptyState } from '@/shared/ui/empty-state'
import { Chat } from './Chat'
import { ResidentCard } from './ResidentCard'
import { TicketHeader } from './TicketHeader'

function parseTicketId(value: string | undefined): number | null {
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

function TicketNotFound() {
  return (
    <EmptyState
      icon={<FileQuestion size={48} strokeWidth={1.5} />}
      title="Обращение не найдено"
      action={
        <Button asChild variant="secondary">
          <Link to={routePaths.staff}>К списку</Link>
        </Button>
      }
    />
  )
}

function TicketView({ id }: { id: number }) {
  const ticket = useTicket(id)

  if (ticket.isPending) {
    return <div className="m-auto text-sm text-fg-3">Загрузка…</div>
  }
  if (ticket.isError) {
    return isApiError(ticket.error, 404) ? (
      <TicketNotFound />
    ) : (
      <EmptyState
        icon={<SearchX size={48} strokeWidth={1.5} />}
        title="Не удалось загрузить обращение"
        text={ticket.error.message}
        action={<Button onClick={() => void ticket.refetch()}>Повторить</Button>}
      />
    )
  }

  // The chat is the product: header with actions, the resident pinned on top, then the dialogue.
  return (
    <section className="flex min-w-0 flex-1 flex-col">
      <TicketHeader ticket={ticket.data} />
      <ResidentCard ticket={ticket.data} />
      <Chat ticket={ticket.data} />
    </section>
  )
}

export function TicketPage() {
  const { id } = useParams()
  const ticketId = parseTicketId(id)
  return ticketId === null ? <TicketNotFound /> : <TicketView key={ticketId} id={ticketId} />
}
