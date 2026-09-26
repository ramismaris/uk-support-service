import { Button } from '@maxhub/max-ui'
import { Search, SearchX, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'
import { EmptyState } from '@/shared/ui/empty-state'
import { NavMenuButton } from '@/widgets/app-shell'
import { parseUserSearch, USER_FILTERS, userFilterLabels, userSearchToParams } from '../lib/filters'
import { useUsers } from '../model/users'
import { UserRow } from './UserRow'

const SEARCH_DELAY_MS = 300

export function UserList() {
  const [params, setParams] = useSearchParams()
  const search = parseUserSearch(params)
  const [typed, setTyped] = useState(search.q)
  const users = useUsers(search)
  const activeId = Number(useParams().id)

  // Typing is debounced into the URL, which drives the query.
  useEffect(() => {
    if (typed === search.q) {
      return
    }
    const timer = setTimeout(
      () => setParams(userSearchToParams({ filter: search.filter, q: typed }), { replace: true }),
      SEARCH_DELAY_MS,
    )
    return () => clearTimeout(timer)
  }, [typed, search.q, search.filter, setParams])

  const items = users.data?.pages.flatMap((page) => page.items) ?? []
  const total = users.data?.pages.at(-1)?.total ?? 0

  const body = () => {
    if (users.isPending) {
      return <div className="p-6 text-center text-sm text-fg-3">Загрузка…</div>
    }
    if (users.isError) {
      return (
        <EmptyState
          icon={<SearchX size={48} strokeWidth={1.5} />}
          title="Не удалось загрузить пользователей"
          text={users.error.message}
          action={<Button onClick={() => void users.refetch()}>Повторить</Button>}
        />
      )
    }
    if (items.length === 0) {
      return (
        <EmptyState
          icon={<UserRound size={48} strokeWidth={1.5} />}
          title="Никого не нашли"
          action={
            search.q || search.filter !== 'all' ? (
              <Button
                variant="secondary"
                onClick={() => {
                  setTyped('')
                  setParams({})
                }}
              >
                Сбросить поиск
              </Button>
            ) : undefined
          }
        />
      )
    }
    return (
      <>
        {items.map((user) => (
          <UserRow key={user.id} user={user} active={user.id === activeId} />
        ))}
        {users.hasNextPage && (
          <div className="flex flex-col items-center gap-2 p-4 text-xs text-fg-3">
            <span>
              {items.length} из {total}
            </span>
            <Button
              variant="secondary"
              size="small"
              loading={users.isFetchingNextPage}
              onClick={() => void users.fetchNextPage()}
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
      <div className="flex flex-col gap-2 border-b border-line p-3">
        <div className="flex items-center gap-2">
          <NavMenuButton />
          <h1 className="text-lg font-semibold">Пользователи</h1>
        </div>
        <label className="flex items-center gap-2 rounded-xl bg-fill px-3 py-2 focus-within:ring-2 focus-within:ring-brand/40">
          <Search size={16} strokeWidth={2} className="shrink-0 text-fg-3" />
          <input
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
            placeholder="Имя, ник, телефон или Max id"
            className="min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-fg-3"
          />
        </label>
        <div className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 whitespace-nowrap [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {USER_FILTERS.map((filter) => (
            <button
              key={filter}
              type="button"
              aria-pressed={search.filter === filter}
              onClick={() => setParams(userSearchToParams({ filter, q: search.q }))}
              className={`rounded-full px-3 py-1 text-sm transition-colors ${
                search.filter === filter
                  ? 'bg-brand/12 font-medium text-brand'
                  : 'text-fg-2 hover:bg-hover'
              }`}
            >
              {userFilterLabels[filter]}
            </button>
          ))}
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">{body()}</div>
    </>
  )
}
