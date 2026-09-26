import { Button } from '@maxhub/max-ui'
import { Inbox, SearchX } from 'lucide-react'
import { useSearchParams } from 'react-router'
import { useTicketList } from '@/entities/ticket'
import { EmptyState } from '@/shared/ui/empty-state'
import { animations, LottieAnimation } from '@/shared/ui/lottie'
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
      return (
        <div aria-busy="true" aria-label="Загрузка">
          {[0, 1, 2, 3].map((row) => (
            <div key={row} className="flex flex-col gap-2 border-b border-line px-3 py-3">
              <div className="h-4 w-32 animate-pulse rounded bg-fill" />
              <div className="h-4 w-full animate-pulse rounded bg-fill" />
              <div className="h-3 w-48 animate-pulse rounded bg-fill" />
            </div>
          ))}
        </div>
      )
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
        <EmptyState
          icon={<Inbox size={48} strokeWidth={1.5} />}
          title="Обращений нет"
          animation={
            <LottieAnimation
              src={animations.emptyList}
              speed={0.6}
              repeatDelay={1500}
              className="size-24"
            />
          }
        />
      )
    }
    return (
      <>
        {tickets.map((ticket) => (
          <TicketRow key={ticket.id} ticket={ticket} />
        ))}
        {list.hasNextPage && (
          <div className="flex flex-col items-center gap-2 p-4 text-xs text-fg-3">
            <span>
              {tickets.length} из {total}
            </span>
            <Button
              variant="secondary"
              size="small"
              loading={list.isFetchingNextPage}
              onClick={() => void list.fetchNextPage()}
            >
              Показать ещё
            </Button>
          </div>
        )}
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
