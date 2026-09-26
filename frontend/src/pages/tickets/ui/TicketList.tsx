import { Button } from '@maxhub/max-ui'
import { Inbox, SearchX } from 'lucide-react'
import { useSearchParams } from 'react-router'
import { useTicketList } from '@/entities/ticket'
import { EmptyState } from '@/shared/ui/empty-state'
import { parseTicketFilters, ticketFiltersToSearch } from '../lib/filters'
import { TicketFiltersBar } from './TicketFiltersBar'
import { TicketRow } from './TicketRow'

export function TicketList() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = parseTicketFilters(searchParams)
  const list = useTicketList(filters)
  const tickets = list.data?.pages.flatMap((page) => page.items) ?? []
  const total = list.data?.pages.at(-1)?.total ?? 0
  const filtered = filters.status !== null || filters.mine

  const body = () => {
    if (list.isPending) {
      return <div className="p-6 text-center text-sm text-neutral-500">Загрузка…</div>
    }
    if (list.isError) {
      return (
        <EmptyState
          icon={<SearchX size={48} strokeWidth={1.5} />}
          title="Не удалось загрузить обращения"
          text={list.error.message}
          action={<Button onClick={() => void list.refetch()}>Повторить</Button>}
        />
      )
    }
    if (tickets.length === 0) {
      return filtered ? (
        <EmptyState
          icon={<SearchX size={48} strokeWidth={1.5} />}
          title="По фильтру ничего не найдено"
          action={
            <Button variant="secondary" onClick={() => setSearchParams({})}>
              Сбросить фильтры
            </Button>
          }
        />
      ) : (
        <EmptyState icon={<Inbox size={48} strokeWidth={1.5} />} title="Обращений нет" />
      )
    }
    return (
      <>
        {tickets.map((ticket) => (
          <TicketRow key={ticket.id} ticket={ticket} />
        ))}
        <div className="flex flex-col items-center gap-2 p-4 text-xs text-neutral-500">
          <span>
            {tickets.length} из {total}
          </span>
          {list.hasNextPage && (
            <Button
              variant="secondary"
              size="small"
              loading={list.isFetchingNextPage}
              onClick={() => void list.fetchNextPage()}
            >
              Показать ещё
            </Button>
          )}
        </div>
      </>
    )
  }

  return (
    <>
      <TicketFiltersBar
        filters={filters}
        onChange={(next) => setSearchParams(ticketFiltersToSearch(next))}
      />
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">{body()}</div>
    </>
  )
}
