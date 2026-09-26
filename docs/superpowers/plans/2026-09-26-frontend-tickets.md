# Фронтенд: обращения, чат, статусы (Ф2 + Ф3 + Ф4) — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Панель менеджера: список активных обращений с фильтрами, экран обращения с чатом (текст + файлы), детали, смена статусов, обновления в реальном времени через WebSocket, переход по кнопке «Открыть» из Max.

**Architecture:** FSD. `entities/ticket` и `entities/message` — типы, запросы TanStack Query, ключи кэша, функции для реалтайма, мелкий UI. Весь экран — слайс `pages/tickets` (layout-роут + список + обращение). `shared/lib/ws` — доменно-нейтральный переподключающийся WebSocket и стор статуса связи; `app/realtime` раскладывает события по кэшам через чистую функцию `planRealtimeUpdate`. Сообщения дописываются в кэш напрямую, события обращений инвалидируют списки и карточку.

**Tech Stack:** как в фундаменте + `lucide-react`, `@lottiefiles/dotlottie-react`.

**Spec:** [docs/superpowers/specs/2026-09-26-frontend-tickets-design.md](../specs/2026-09-26-frontend-tickets-design.md)

## Global Constraints

- Все команды фронтенда — из `frontend/`, только pnpm. Проверка — `bash scripts/check.sh`.
- Ветка `feat/frontend-tickets` (уже создана от `feat/frontend-foundation`). В `main` не вливать.
- Коммиты: Conventional Commits, область `web` / `docs`, **только заголовок, без тела и трейлеров**.
- FSD строго: импорт только вниз; без кросс-импортов слайсов одного слоя; снаружи — только через `index.ts`; внутри слайса — относительные импорты. Код одного потребителя живёт в нём. Steiger зелёный; правило, которое не удаётся соблюсти, — остановиться и спросить.
- Иконки — только `lucide-react`; эмодзи в интерфейсе нет.
- Тексты интерфейса — на русском; код и комментарии — на английском.
- Max UI 0.5.0: у `Button` проп `variant` (`primary | secondary | ghost | destructive | …`), `size` (`xsmall | small | medium | large`), `stretched`, `loading`, `asChild`. `Textarea` принимает пропсы `<textarea>`. Иконок в Max UI почти нет.
- Lottie-анимации вставляются **только после согласования подбора с пользователем** (Task 9, шаг-остановка).
- `schema.d.ts` — только `pnpm gen:api`.
- Бэкенд для ручной проверки: `backend/` → `docker compose up -d --build --wait` → `docker compose exec -T api python scripts/seed.py`. На этой машине перед сборкой: `sed -i 's/\r$//' docker-entrypoint.sh`, после — `git checkout -- docker-entrypoint.sh` (CRLF, см. спек).

## Review Focus

- Своё отправленное сообщение приходит дважды (ответ POST и `message_created`) → в чате ровно одно. Тест: Task 3 (`appendMessage` дубль).
- Обрыв WebSocket и возврат → пропущенные события не приходят, данные должны перечитаться; 4401 → выход на логин, 4403 → без бесконечного переподключения. Тесты: Task 4 (`planRealtimeUpdate` reconnected, `shouldReconnect`, `reconnectDelay`).
- Мусорный `start_param` (`ticket_abc`, `ticket_-1`, `foo`, пусто) → обычный `/staff`, без падения. Тест: Task 8.
- Выбор 11 фото, фото + документ, файл 25 МБ, пустое сообщение из пробелов → отправка заблокирована с понятным текстом. Тест: Task 6 (`validateMessage`, `hasContent`).
- Мусорные query-параметры фильтра (`?status=CLOSED&mine=yes`) → фильтр сброшен до допустимых значений, запрос к API валиден. Тест: Task 5 (`parseTicketFilters`).

---

## Файловая карта

```
frontend/
├── vite.config.ts                                   host 127.0.0.1, ws-прокси
└── src/
    ├── app/
    │   ├── realtime/{plan-realtime-update.ts(+test), StaffRealtime.tsx}
    │   └── routes/{router.tsx, RoleRedirect.tsx, deep-link.ts(+test)}
    ├── pages/
    │   ├── staff-home/                              удаляется
    │   └── tickets/
    │       ├── index.ts
    │       ├── api/{send-message.ts, change-status.ts, mark-read.ts}
    │       ├── lib/{filters.ts(+test), message-rules.ts(+test), status-actions.ts(+test)}
    │       ├── model/{use-send-message.ts, use-change-status.ts, use-mark-read.ts}
    │       └── ui/{TicketsLayout, TicketsIndexPage, TicketList, TicketRow, TicketFiltersBar,
    │               TicketPage, TicketHeader, Chat, Composer, TicketDetails, StatusActions,
    │               RejectDialog, DetailsDrawer}.tsx
    ├── widgets/app-shell/{model/nav.ts, ui/AppShell.tsx}   высота на весь экран, активный пункт
    ├── entities/
    │   ├── ticket/{index.ts, model/{types.ts, status.ts}, api/{keys.ts, queries.ts(+test)},
    │   │           ui/{TicketStatusBadge.tsx, UrgentMark.tsx}}
    │   └── message/{index.ts, model/types.ts, api/{keys.ts, queries.ts, append-message.ts(+test)},
    │                ui/MessageBubble.tsx}
    └── shared/
        ├── config/routes.ts                          + ticket, ticketPath()
        ├── lib/format/{index.ts, time.ts(+test), file-size.ts(+test)}
        ├── lib/media-query/{index.ts, use-media-query.ts}
        ├── lib/ws/{index.ts, reconnecting-socket.ts, backoff.ts(+test), status-store.ts}
        └── ui/{empty-state, lottie}/
```

---

### Task 1: Зависимости, инфраструктура, общие утилиты

**Files:**
- Modify: `frontend/package.json` (через pnpm), `frontend/vite.config.ts`, `frontend/src/shared/config/routes.ts`, `frontend/src/shared/config/index.ts`
- Create: `frontend/src/shared/lib/format/{time.ts, file-size.ts, index.ts}`, `frontend/src/shared/lib/media-query/{use-media-query.ts, index.ts}`, `frontend/src/shared/ui/empty-state/{EmptyState.tsx, index.ts}`
- Test: `frontend/src/shared/lib/format/time.test.ts`, `frontend/src/shared/lib/format/file-size.test.ts`

**Interfaces:**
- Produces:
  - `@/shared/config`: `routePaths.ticket = '/staff/tickets/:id'`, `ticketPath(id: number): string`;
  - `@/shared/lib/format`: `formatRelativeTime(iso: string, now?: Date): string`, `formatDateTime(iso: string, now?: Date): string`, `formatFileSize(bytes: number): string`;
  - `@/shared/lib/media-query`: `useMediaQuery(query: string): boolean`, `breakpoints = { lg: '(min-width: 1024px)', xl: '(min-width: 1280px)' }`;
  - `@/shared/ui/empty-state`: `EmptyState({ icon: ReactNode, title: string, text?: string, action?: ReactNode, animation?: ReactNode })`.

- [ ] **Step 1: Зависимости и Vite**

```bash
pnpm add lucide-react @lottiefiles/dotlottie-react
```

`vite.config.ts` — блок `server` заменить на:
```ts
  server: {
    // localhost resolves to ::1 on some machines and the browser then cannot reach the server.
    host: '127.0.0.1',
    proxy: { '/api': { target: 'http://localhost:8000', ws: true } },
  },
```

- [ ] **Step 2: Роуты**

`shared/config/routes.ts`:
```ts
export const routePaths = {
  home: '/',
  login: '/login',
  staff: '/staff',
  ticket: '/staff/tickets/:id',
  client: '/client',
} as const

export function ticketPath(id: number): string {
  return `/staff/tickets/${id}`
}
```
`shared/config/index.ts`:
```ts
export { isDevAuthEnabled } from './env'
export { routePaths, ticketPath } from './routes'
```

- [ ] **Step 3: Тесты форматирования**

`shared/lib/format/time.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { formatDateTime, formatRelativeTime } from './time'

// Local-time dates keep the tests independent of the machine's timezone.
const now = new Date(2026, 8, 26, 15, 30)
const iso = (...args: [number, number, number, number, number]) => new Date(...args).toISOString()

describe('formatRelativeTime', () => {
  it('says "только что" within a minute', () => {
    expect(formatRelativeTime(iso(2026, 8, 26, 15, 29), now)).toBe('только что')
  })

  it('counts minutes within an hour', () => {
    expect(formatRelativeTime(iso(2026, 8, 26, 15, 5), now)).toBe('25 мин')
  })

  it('shows the time earlier today', () => {
    expect(formatRelativeTime(iso(2026, 8, 26, 9, 7), now)).toBe('09:07')
  })

  it('says "вчера" for yesterday', () => {
    expect(formatRelativeTime(iso(2026, 8, 25, 23, 0), now)).toBe('вчера')
  })

  it('shows day and month for older dates this year', () => {
    expect(formatRelativeTime(iso(2026, 2, 3, 10, 0), now)).toBe('3 мар.')
  })

  it('adds the year for previous years', () => {
    expect(formatRelativeTime(iso(2025, 11, 31, 10, 0), now)).toBe('31 дек. 2025 г.')
  })
})

describe('formatDateTime', () => {
  it('shows only the time today', () => {
    expect(formatDateTime(iso(2026, 8, 26, 9, 7), now)).toBe('09:07')
  })

  it('shows day, month and time on other days', () => {
    expect(formatDateTime(iso(2026, 8, 20, 18, 45), now)).toBe('20 сент., 18:45')
  })
})
```

`shared/lib/format/file-size.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { formatFileSize } from './file-size'

describe('formatFileSize', () => {
  it.each([
    [512, '512 Б'],
    [2048, '2 КБ'],
    [1536000, '1,5 МБ'],
    [20 * 1024 * 1024, '20 МБ'],
  ])('%i → %s', (bytes, text) => {
    expect(formatFileSize(bytes)).toBe(text)
  })
})
```

- [ ] **Step 4: Запустить — падают**

Run: `pnpm exec vitest run src/shared/lib/format`
Expected: FAIL — `Failed to resolve import "./time"` и `"./file-size"`.

- [ ] **Step 5: Реализация форматирования**

`shared/lib/format/time.ts`:
```ts
const MINUTE = 60_000
const HOUR = 60 * MINUTE

const timeFormat = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' })
const dayMonthFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' })
const fullDateFormat = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
  )
}

function isYesterday(date: Date, now: Date): boolean {
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  return isSameDay(date, yesterday)
}

export function formatRelativeTime(iso: string, now: Date = new Date()): string {
  const date = new Date(iso)
  const diff = now.getTime() - date.getTime()
  if (diff < MINUTE) {
    return 'только что'
  }
  if (diff < HOUR) {
    return `${Math.floor(diff / MINUTE)} мин`
  }
  if (isSameDay(date, now)) {
    return timeFormat.format(date)
  }
  if (isYesterday(date, now)) {
    return 'вчера'
  }
  if (date.getFullYear() === now.getFullYear()) {
    return dayMonthFormat.format(date)
  }
  return fullDateFormat.format(date)
}

export function formatDateTime(iso: string, now: Date = new Date()): string {
  const date = new Date(iso)
  const time = timeFormat.format(date)
  return isSameDay(date, now) ? time : `${dayMonthFormat.format(date)}, ${time}`
}
```

`shared/lib/format/file-size.ts`:
```ts
const KB = 1024
const MB = 1024 * KB

const numberFormat = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 })

export function formatFileSize(bytes: number): string {
  if (bytes < KB) {
    return `${bytes} Б`
  }
  if (bytes < MB) {
    return `${numberFormat.format(bytes / KB)} КБ`
  }
  return `${numberFormat.format(bytes / MB)} МБ`
}
```

`shared/lib/format/index.ts`:
```ts
export { formatFileSize } from './file-size'
export { formatDateTime, formatRelativeTime } from './time'
```

- [ ] **Step 6: Запустить — проходят**

Run: `pnpm exec vitest run src/shared/lib/format`
Expected: PASS (12 тестов). Если строки `Intl` отличаются (например, `сент.` vs `сен.` в версии ICU Node) — это расхождение данных ICU, а не логики: поправить **ожидания** под фактический вывод `Intl` на этой машине и записать это в журнал.

- [ ] **Step 7: `media-query` и `EmptyState`**

`shared/lib/media-query/use-media-query.ts`:
```ts
import { useCallback, useSyncExternalStore } from 'react'

export const breakpoints = {
  lg: '(min-width: 1024px)',
  xl: '(min-width: 1280px)',
} as const

export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const media = window.matchMedia(query)
      media.addEventListener('change', onChange)
      return () => media.removeEventListener('change', onChange)
    },
    [query],
  )
  return useSyncExternalStore(subscribe, () => window.matchMedia(query).matches)
}
```
`shared/lib/media-query/index.ts`:
```ts
export { breakpoints, useMediaQuery } from './use-media-query'
```

`shared/ui/empty-state/EmptyState.tsx`:
```tsx
import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: ReactNode
  title: string
  text?: string
  action?: ReactNode
  // Lottie animation; replaces the icon when given.
  animation?: ReactNode
}

export function EmptyState({ icon, title, text, action, animation }: EmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="flex size-32 items-center justify-center text-neutral-400">
        {animation ?? icon}
      </div>
      <div className="font-medium">{title}</div>
      {text && <p className="max-w-xs text-sm text-neutral-500 dark:text-neutral-400">{text}</p>}
      {action}
    </div>
  )
}
```
`shared/ui/empty-state/index.ts`:
```ts
export { EmptyState } from './EmptyState'
```

- [ ] **Step 8: Проверка и коммит**

Run: `pnpm exec tsc -b && pnpm exec prettier --write src vite.config.ts > /dev/null && pnpm exec eslint . && pnpm exec vitest run`
Expected: всё зелёное.

```bash
git add frontend
git commit -m "feat(web): add formatting, media query and empty state helpers"
```

---

### Task 2: `entities/ticket`

**Files:**
- Create: `frontend/src/entities/ticket/{model/types.ts, model/status.ts, api/keys.ts, api/queries.ts, ui/TicketStatusBadge.tsx, ui/UrgentMark.tsx, index.ts}`
- Test: `frontend/src/entities/ticket/api/queries.test.ts`

**Interfaces:**
- Consumes: `api`, `unwrap`, `components` (`@/shared/api`).
- Produces (`@/entities/ticket`):
  - типы `TicketListItem`, `TicketDetail`, `TicketStatus`, `ActiveTicketStatus = 'NEW' | 'IN_PROGRESS' | 'WAITING_CLIENT'`, `TicketFilters = { status: ActiveTicketStatus | null; mine: boolean }`, `TicketPage = { total: number; items: TicketListItem[] }`;
  - `statusLabels: Record<TicketStatus, string>`, `ticketTypeLabels: Record<TicketType, string>`;
  - `ticketKeys` (`all`, `lists()`, `list(filters)`, `details()`, `detail(id)`);
  - `useTicketList(filters)` (infinite), `useTicket(id)`, `nextPageOffset(pages: TicketPage[]): number | undefined`;
  - `invalidateTicketLists(queryClient)`, `invalidateTicket(queryClient, id)`, `invalidateAllTickets(queryClient)`;
  - UI: `TicketStatusBadge({ status })`, `UrgentMark()`.

- [ ] **Step 1: Тест `queries.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import type { TicketPage } from '../model/types'
import { nextPageOffset } from './queries'

const page = (count: number, total: number): TicketPage => ({
  total,
  items: Array.from({ length: count }, () => ({}) as TicketPage['items'][number]),
})

describe('nextPageOffset', () => {
  it('asks for the next page while fewer than total are loaded', () => {
    expect(nextPageOffset([page(50, 120)])).toBe(50)
    expect(nextPageOffset([page(50, 120), page(50, 120)])).toBe(100)
  })

  it('stops when everything is loaded', () => {
    expect(nextPageOffset([page(50, 120), page(50, 120), page(20, 120)])).toBeUndefined()
    expect(nextPageOffset([page(0, 0)])).toBeUndefined()
  })
})
```

- [ ] **Step 2: Запустить — падает**

Run: `pnpm exec vitest run src/entities/ticket`
Expected: FAIL — не найден `../model/types` / `./queries`.

- [ ] **Step 3: Модель**

`model/types.ts`:
```ts
import type { components } from '@/shared/api'

export type TicketListItem = components['schemas']['TicketListItemResponse']
export type TicketDetail = components['schemas']['TicketDetailResponse']
export type TicketStatus = components['schemas']['TicketStatus']
export type TicketType = components['schemas']['TicketType']
export type ActiveTicketStatus = 'NEW' | 'IN_PROGRESS' | 'WAITING_CLIENT'

export interface TicketFilters {
  status: ActiveTicketStatus | null
  mine: boolean
}

export interface TicketPage {
  total: number
  items: TicketListItem[]
}
```

`model/status.ts`:
```ts
import type { TicketStatus, TicketType } from './types'

export const statusLabels: Record<TicketStatus, string> = {
  NEW: 'Новое',
  IN_PROGRESS: 'В работе',
  WAITING_CLIENT: 'Ждёт ответа',
  CLOSED: 'Закрыто',
  REJECTED: 'Отклонено',
}

export const statusTones: Record<TicketStatus, string> = {
  NEW: 'bg-brand/10 text-brand',
  IN_PROGRESS: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  WAITING_CLIENT: 'bg-violet-500/15 text-violet-700 dark:text-violet-300',
  CLOSED: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  REJECTED: 'bg-neutral-500/15 text-neutral-600 dark:text-neutral-400',
}

export const ticketTypeLabels: Record<TicketType, string> = {
  REQUEST: 'Заявка',
  QUESTION: 'Вопрос',
}
```

- [ ] **Step 4: API**

`api/keys.ts`:
```ts
import type { TicketFilters } from '../model/types'

export const ticketKeys = {
  all: ['tickets'] as const,
  lists: () => [...ticketKeys.all, 'list'] as const,
  list: (filters: TicketFilters) => [...ticketKeys.lists(), filters] as const,
  details: () => [...ticketKeys.all, 'detail'] as const,
  detail: (id: number) => [...ticketKeys.details(), id] as const,
}
```

`api/queries.ts`:
```ts
import { useInfiniteQuery, useQuery, type QueryClient } from '@tanstack/react-query'
import { api, unwrap } from '@/shared/api'
import type { TicketFilters, TicketPage } from '../model/types'
import { ticketKeys } from './keys'

const PAGE_SIZE = 50

export function nextPageOffset(pages: TicketPage[]): number | undefined {
  const loaded = pages.reduce((count, page) => count + page.items.length, 0)
  const total = pages.at(-1)?.total ?? 0
  return loaded < total ? loaded : undefined
}

export function useTicketList(filters: TicketFilters) {
  return useInfiniteQuery({
    queryKey: ticketKeys.list(filters),
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/api/v1/staff/tickets', {
          params: {
            query: {
              status: filters.status ?? undefined,
              mine: filters.mine || undefined,
              skip: pageParam,
              limit: PAGE_SIZE,
            },
          },
        }),
      ),
    initialPageParam: 0,
    getNextPageParam: (_lastPage, pages) => nextPageOffset(pages),
  })
}

export function useTicket(id: number) {
  return useQuery({
    queryKey: ticketKeys.detail(id),
    queryFn: () =>
      unwrap(api.GET('/api/v1/staff/tickets/{ticket_id}', { params: { path: { ticket_id: id } } })),
  })
}

export function invalidateTicketLists(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
}

export function invalidateTicket(queryClient: QueryClient, id: number): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: ticketKeys.detail(id) })
}

export function invalidateAllTickets(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: ticketKeys.all })
}
```

- [ ] **Step 5: Запустить — проходит**

Run: `pnpm exec vitest run src/entities/ticket`
Expected: PASS (2 теста).

- [ ] **Step 6: UI и public API**

`ui/TicketStatusBadge.tsx`:
```tsx
import { statusLabels, statusTones } from '../model/status'
import type { TicketStatus } from '../model/types'

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusTones[status]}`}
    >
      {statusLabels[status]}
    </span>
  )
}
```

`ui/UrgentMark.tsx`:
```tsx
import { Siren } from 'lucide-react'

export function UrgentMark() {
  return (
    <span className="inline-flex text-red-600 dark:text-red-400" title="Срочное" aria-label="Срочное">
      <Siren size={16} strokeWidth={2} />
    </span>
  )
}
```

`index.ts`:
```ts
export { ticketKeys } from './api/keys'
export {
  invalidateAllTickets,
  invalidateTicket,
  invalidateTicketLists,
  nextPageOffset,
  useTicket,
  useTicketList,
} from './api/queries'
export { statusLabels, ticketTypeLabels } from './model/status'
export type {
  ActiveTicketStatus,
  TicketDetail,
  TicketFilters,
  TicketListItem,
  TicketPage,
  TicketStatus,
} from './model/types'
export { TicketStatusBadge } from './ui/TicketStatusBadge'
export { UrgentMark } from './ui/UrgentMark'
```

- [ ] **Step 7: Проверка и коммит**

Run: `pnpm exec tsc -b && pnpm exec prettier --write src > /dev/null && pnpm exec eslint . && pnpm exec vitest run`
Expected: зелёное. Steiger сообщит «no references» для `entities/ticket` — временно, до Task 4/5 (как в фундаменте).

```bash
git add frontend/src/entities/ticket
git commit -m "feat(web): add ticket entity"
```

---

### Task 3: `entities/message`

**Files:**
- Create: `frontend/src/entities/message/{model/types.ts, api/keys.ts, api/queries.ts, api/append-message.ts, ui/MessageBubble.tsx, index.ts}`
- Test: `frontend/src/entities/message/api/append-message.test.ts`

**Interfaces:**
- Consumes: `api`, `unwrap`, `components`; `formatDateTime`, `formatFileSize` (`@/shared/lib/format`).
- Produces (`@/entities/message`): типы `Message`, `MessageFile`; `messageKeys` (`all`, `list(ticketId)`); `useMessages(ticketId)`; `appendMessage(queryClient, message): void`; `invalidateAllMessages(queryClient)`; UI `MessageBubble({ message })`.

- [ ] **Step 1: Тест `append-message.test.ts`**

```ts
import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import type { Message } from '../model/types'
import { appendMessage } from './append-message'
import { messageKeys } from './keys'

const message = (id: number, ticketId = 1042): Message => ({
  id,
  ticket_id: ticketId,
  sender_type: 'CLIENT',
  author: null,
  text: `m${id}`,
  files: [],
  created_at: '2026-09-26T12:00:00Z',
})

describe('appendMessage', () => {
  it('appends to the cached chat of that ticket', () => {
    const queryClient = new QueryClient()
    queryClient.setQueryData(messageKeys.list(1042), [message(1)])
    appendMessage(queryClient, message(2))
    expect(queryClient.getQueryData<Message[]>(messageKeys.list(1042))?.map((m) => m.id)).toEqual([
      1, 2,
    ])
  })

  it('ignores a message that is already in the chat', () => {
    const queryClient = new QueryClient()
    queryClient.setQueryData(messageKeys.list(1042), [message(1), message(2)])
    appendMessage(queryClient, message(2))
    expect(queryClient.getQueryData<Message[]>(messageKeys.list(1042))).toHaveLength(2)
  })

  it('does nothing when the chat is not loaded', () => {
    const queryClient = new QueryClient()
    appendMessage(queryClient, message(1, 7))
    expect(queryClient.getQueryData(messageKeys.list(7))).toBeUndefined()
  })
})
```

- [ ] **Step 2: Запустить — падает**

Run: `pnpm exec vitest run src/entities/message`
Expected: FAIL — не найдены модули.

- [ ] **Step 3: Реализация**

`model/types.ts`:
```ts
import type { components } from '@/shared/api'

export type Message = components['schemas']['MessageResponse']
export type MessageFile = components['schemas']['FileResponse']
```

`api/keys.ts`:
```ts
export const messageKeys = {
  all: ['messages'] as const,
  list: (ticketId: number) => [...messageKeys.all, ticketId] as const,
}
```

`api/append-message.ts`:
```ts
import type { QueryClient } from '@tanstack/react-query'
import type { Message } from '../model/types'
import { messageKeys } from './keys'

// A sent message comes back twice: in the POST response and as a message_created event.
export function appendMessage(queryClient: QueryClient, message: Message): void {
  queryClient.setQueryData<Message[]>(messageKeys.list(message.ticket_id), (messages) => {
    if (!messages || messages.some((existing) => existing.id === message.id)) {
      return messages
    }
    return [...messages, message]
  })
}
```

`api/queries.ts`:
```ts
import { useQuery, type QueryClient } from '@tanstack/react-query'
import { api, unwrap } from '@/shared/api'
import { messageKeys } from './keys'

export function useMessages(ticketId: number) {
  return useQuery({
    queryKey: messageKeys.list(ticketId),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/staff/tickets/{ticket_id}/messages', {
          params: { path: { ticket_id: ticketId } },
        }),
      ),
  })
}

export function invalidateAllMessages(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: messageKeys.all })
}
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/entities/message`
Expected: PASS (3 теста).

- [ ] **Step 5: `MessageBubble` и public API**

`ui/MessageBubble.tsx`:
```tsx
import { FileText } from 'lucide-react'
import { formatDateTime, formatFileSize } from '@/shared/lib/format'
import type { Message, MessageFile } from '../model/types'

function Attachment({ file }: { file: MessageFile }) {
  if (file.mime.startsWith('image/')) {
    return (
      <a href={file.url} target="_blank" rel="noreferrer" className="block">
        <img
          src={file.url}
          alt={file.original_name ?? 'Фото'}
          className="max-h-60 rounded-lg object-cover"
          loading="lazy"
        />
      </a>
    )
  }
  return (
    <a
      href={file.url}
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-2 rounded-lg bg-black/5 px-3 py-2 text-sm dark:bg-white/10"
    >
      <FileText size={20} strokeWidth={2} className="shrink-0" />
      <span className="min-w-0 truncate">{file.original_name ?? 'Файл'}</span>
      <span className="shrink-0 text-neutral-500">{formatFileSize(file.size)}</span>
    </a>
  )
}

export function MessageBubble({ message }: { message: Message }) {
  if (message.sender_type === 'SYSTEM') {
    return (
      <div className="mx-auto max-w-md px-4 text-center text-xs text-neutral-500 dark:text-neutral-400">
        {message.text}
      </div>
    )
  }

  const fromStaff = message.sender_type === 'STAFF'
  return (
    <div className={`flex ${fromStaff ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`flex max-w-[80%] flex-col gap-2 rounded-2xl px-3 py-2 ${
          fromStaff
            ? 'rounded-br-md bg-brand text-white'
            : 'rounded-bl-md bg-white shadow-sm dark:bg-neutral-800'
        }`}
      >
        {fromStaff && message.author && (
          <div className="text-xs font-medium opacity-80">{message.author.first_name}</div>
        )}
        {message.files.map((file) => (
          <Attachment key={file.id} file={file} />
        ))}
        {message.text && <p className="whitespace-pre-wrap break-words">{message.text}</p>}
        <div className="self-end text-[11px] opacity-60">{formatDateTime(message.created_at)}</div>
      </div>
    </div>
  )
}
```

`index.ts`:
```ts
export { appendMessage } from './api/append-message'
export { messageKeys } from './api/keys'
export { invalidateAllMessages, useMessages } from './api/queries'
export type { Message, MessageFile } from './model/types'
export { MessageBubble } from './ui/MessageBubble'
```

- [ ] **Step 6: Проверка и коммит**

Run: `pnpm exec tsc -b && pnpm exec prettier --write src > /dev/null && pnpm exec eslint . && pnpm exec vitest run`
Expected: зелёное (Steiger «no references» — временно).

```bash
git add frontend/src/entities/message
git commit -m "feat(web): add message entity"
```

---

### Task 4: WebSocket и реалтайм

**Files:**
- Create: `frontend/src/shared/lib/ws/{backoff.ts, reconnecting-socket.ts, status-store.ts, index.ts}`, `frontend/src/app/realtime/{plan-realtime-update.ts, StaffRealtime.tsx}`
- Modify: `frontend/src/app/routes/router.tsx` (подключить `StaffRealtime` в ветку сотрудника)
- Test: `frontend/src/shared/lib/ws/backoff.test.ts`, `frontend/src/app/realtime/plan-realtime-update.test.ts`

**Interfaces:**
- Consumes: `appendMessage`, `invalidateAllMessages`, `Message` (`@/entities/message`); `invalidateTicketLists`, `invalidateTicket`, `invalidateAllTickets` (`@/entities/ticket`); `useSessionStore` (`@/entities/session`).
- Produces:
  - `@/shared/lib/ws`: `reconnectDelay(attempt: number): number`, `shouldReconnect(code: number): boolean`, `createReconnectingSocket(options): { close(): void }`, `useSocketStatus` (Zustand: `online: boolean`, `setOnline(value)`);
  - `app/realtime`: `planRealtimeUpdate(event: unknown): RealtimeAction[]`, компонент `StaffRealtime`.

- [ ] **Step 1: Тесты `backoff.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import { reconnectDelay, shouldReconnect } from './backoff'

describe('reconnectDelay', () => {
  it.each([
    [0, 1000],
    [1, 2000],
    [3, 8000],
    [4, 16000],
    [5, 30000],
    [12, 30000],
  ])('attempt %i waits %i ms', (attempt, delay) => {
    expect(reconnectDelay(attempt)).toBe(delay)
  })
})

describe('shouldReconnect', () => {
  it('stops on auth rejections', () => {
    expect(shouldReconnect(4401)).toBe(false)
    expect(shouldReconnect(4403)).toBe(false)
  })

  it('reconnects on network drops and server restarts', () => {
    expect(shouldReconnect(1006)).toBe(true)
    expect(shouldReconnect(1012)).toBe(true)
  })
})
```

- [ ] **Step 2: Запустить — падает**

Run: `pnpm exec vitest run src/shared/lib/ws`
Expected: FAIL — не найден `./backoff`.

- [ ] **Step 3: `backoff.ts`**

```ts
const BASE_DELAY = 1000
const MAX_DELAY = 30_000

export const CLOSE_UNAUTHORIZED = 4401
export const CLOSE_FORBIDDEN = 4403

export function reconnectDelay(attempt: number): number {
  return Math.min(BASE_DELAY * 2 ** attempt, MAX_DELAY)
}

export function shouldReconnect(code: number): boolean {
  return code !== CLOSE_UNAUTHORIZED && code !== CLOSE_FORBIDDEN
}
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/shared/lib/ws`
Expected: PASS (8 тестов).

- [ ] **Step 5: Сокет и стор статуса**

`status-store.ts`:
```ts
import { create } from 'zustand'

interface SocketStatusState {
  online: boolean
  setOnline: (online: boolean) => void
}

// Optimistic: the indicator appears only after a real drop.
export const useSocketStatus = create<SocketStatusState>()((set) => ({
  online: true,
  setOnline: (online) => set({ online }),
}))
```

`reconnecting-socket.ts`:
```ts
import { reconnectDelay, shouldReconnect } from './backoff'

interface ReconnectingSocketOptions {
  url: () => string
  onMessage: (data: unknown) => void
  // isReconnect: events may have been missed while the socket was down.
  onOpen: (isReconnect: boolean) => void
  onDrop: () => void
  onFatalClose: (code: number) => void
}

export function createReconnectingSocket(options: ReconnectingSocketOptions): { close(): void } {
  let socket: WebSocket | null = null
  let attempt = 0
  let opened = false
  let stopped = false
  let timer: ReturnType<typeof setTimeout> | undefined

  const connect = () => {
    socket = new WebSocket(options.url())
    socket.onopen = () => {
      options.onOpen(opened)
      opened = true
      attempt = 0
    }
    socket.onmessage = (event) => {
      try {
        options.onMessage(JSON.parse(String(event.data)))
      } catch {
        // Not JSON: nothing the panel can act on.
      }
    }
    socket.onclose = (event) => {
      socket = null
      if (stopped) {
        return
      }
      if (!shouldReconnect(event.code)) {
        options.onFatalClose(event.code)
        return
      }
      options.onDrop()
      timer = setTimeout(connect, reconnectDelay(attempt))
      attempt += 1
    }
  }

  connect()

  return {
    close() {
      stopped = true
      clearTimeout(timer)
      socket?.close()
    },
  }
}
```

`index.ts`:
```ts
export { CLOSE_UNAUTHORIZED, reconnectDelay, shouldReconnect } from './backoff'
export { createReconnectingSocket } from './reconnecting-socket'
export { useSocketStatus } from './status-store'
```

- [ ] **Step 6: Тесты `plan-realtime-update.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import { planRealtimeUpdate } from './plan-realtime-update'

const message = {
  id: 7,
  ticket_id: 1042,
  sender_type: 'CLIENT',
  author: null,
  text: 'Течёт',
  files: [],
  created_at: '2026-09-26T12:00:00Z',
}

describe('planRealtimeUpdate', () => {
  it('appends a new chat message', () => {
    expect(planRealtimeUpdate({ type: 'message_created', message })).toEqual([
      { type: 'append-message', message },
    ])
  })

  it('refreshes lists on a new ticket', () => {
    expect(planRealtimeUpdate({ type: 'ticket_created', ticket: { id: 1050 } })).toEqual([
      { type: 'invalidate-lists' },
    ])
  })

  it('refreshes lists and the card on a ticket update', () => {
    expect(planRealtimeUpdate({ type: 'ticket_updated', ticket: { id: 1042 } })).toEqual([
      { type: 'invalidate-lists' },
      { type: 'invalidate-ticket', ticketId: 1042 },
    ])
  })

  it('refreshes everything after a reconnect', () => {
    expect(planRealtimeUpdate({ type: 'reconnected' })).toEqual([{ type: 'invalidate-all' }])
  })

  it.each([
    null,
    'text',
    { type: 'unknown' },
    { type: 'message_created' },
    { type: 'message_created', message: { id: 'x', ticket_id: 1 } },
    { type: 'ticket_updated', ticket: {} },
  ])('ignores malformed event %j', (event) => {
    expect(planRealtimeUpdate(event)).toEqual([])
  })
})
```

- [ ] **Step 7: Запустить — падает**

Run: `pnpm exec vitest run src/app/realtime`
Expected: FAIL — не найден `./plan-realtime-update`.

- [ ] **Step 8: `plan-realtime-update.ts`**

```ts
import type { Message } from '@/entities/message'

export type RealtimeAction =
  | { type: 'append-message'; message: Message }
  | { type: 'invalidate-lists' }
  | { type: 'invalidate-ticket'; ticketId: number }
  | { type: 'invalidate-all' }

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function ticketIdOf(event: Record<string, unknown>): number | null {
  const ticket = event.ticket
  return isObject(ticket) && typeof ticket.id === 'number' ? ticket.id : null
}

function isMessage(value: unknown): value is Message {
  return isObject(value) && typeof value.id === 'number' && typeof value.ticket_id === 'number'
}

// Events come from the network: anything unexpected is ignored rather than trusted.
export function planRealtimeUpdate(event: unknown): RealtimeAction[] {
  if (!isObject(event)) {
    return []
  }
  switch (event.type) {
    case 'message_created':
      return isMessage(event.message) ? [{ type: 'append-message', message: event.message }] : []
    case 'ticket_created':
      return ticketIdOf(event) !== null ? [{ type: 'invalidate-lists' }] : []
    case 'ticket_updated': {
      const ticketId = ticketIdOf(event)
      return ticketId !== null
        ? [{ type: 'invalidate-lists' }, { type: 'invalidate-ticket', ticketId }]
        : []
    }
    case 'reconnected':
      return [{ type: 'invalidate-all' }]
    default:
      return []
  }
}
```

- [ ] **Step 9: Запустить — проходит**

Run: `pnpm exec vitest run src/app/realtime`
Expected: PASS (10 тестов).

- [ ] **Step 10: `StaffRealtime.tsx` и подключение**

```tsx
import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { appendMessage, invalidateAllMessages } from '@/entities/message'
import { useSessionStore } from '@/entities/session'
import { invalidateAllTickets, invalidateTicket, invalidateTicketLists } from '@/entities/ticket'
import { CLOSE_UNAUTHORIZED, createReconnectingSocket, useSocketStatus } from '@/shared/lib/ws'
import { planRealtimeUpdate } from './plan-realtime-update'

function socketUrl(token: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/v1/ws?token=${encodeURIComponent(token)}`
}

export function StaffRealtime() {
  const queryClient = useQueryClient()
  const token = useSessionStore((state) => state.token)

  useEffect(() => {
    if (token === null) {
      return
    }
    const { setOnline } = useSocketStatus.getState()

    const apply = (event: unknown) => {
      for (const action of planRealtimeUpdate(event)) {
        switch (action.type) {
          case 'append-message':
            appendMessage(queryClient, action.message)
            break
          case 'invalidate-lists':
            void invalidateTicketLists(queryClient)
            break
          case 'invalidate-ticket':
            void invalidateTicket(queryClient, action.ticketId)
            break
          case 'invalidate-all':
            void invalidateAllTickets(queryClient)
            void invalidateAllMessages(queryClient)
            break
        }
      }
    }

    const socket = createReconnectingSocket({
      url: () => socketUrl(token),
      onMessage: apply,
      onOpen: (isReconnect) => {
        setOnline(true)
        if (isReconnect) {
          apply({ type: 'reconnected' })
        }
      },
      onDrop: () => setOnline(false),
      onFatalClose: (code) => {
        if (code === CLOSE_UNAUTHORIZED) {
          // Same as a 401 from the REST api: the session is gone.
          useSessionStore.getState().clear()
          queryClient.clear()
        }
      },
    })

    return () => {
      socket.close()
      setOnline(true)
    }
  }, [token, queryClient])

  return null
}
```

`app/routes/router.tsx` — элемент ветки `staff`:
```tsx
        element: (
          <RequireRole allow={isStaff}>
            <StaffRealtime />
            <AppShell />
          </RequireRole>
        ),
```
и импорт `import { StaffRealtime } from '../realtime/StaffRealtime'`.

- [ ] **Step 11: Проверка и коммит**

Run: `bash scripts/check.sh`
Expected: `all checks passed`; Steiger больше не жалуется на `entities/ticket`/`entities/message` (ссылка из `app` не считается слайсом — если «no references» остаётся, это временно до Task 5).

```bash
git add frontend/src
git commit -m "feat(web): add realtime updates over websocket"
```

---

### Task 5: Список обращений и layout

**Files:**
- Create: `frontend/src/pages/tickets/{index.ts, lib/filters.ts, ui/TicketsLayout.tsx, ui/TicketsIndexPage.tsx, ui/TicketList.tsx, ui/TicketRow.tsx, ui/TicketFiltersBar.tsx}`
- Modify: `frontend/src/app/routes/router.tsx`, `frontend/src/widgets/app-shell/ui/AppShell.tsx`
- Delete: `frontend/src/pages/staff-home/`
- Test: `frontend/src/pages/tickets/lib/filters.test.ts`

**Interfaces:**
- Consumes: `useTicketList`, `TicketFilters`, `ActiveTicketStatus`, `TicketListItem`, `TicketStatusBadge`, `UrgentMark`, `ticketTypeLabels` (`@/entities/ticket`); `useSocketStatus`; `EmptyState`; `formatRelativeTime`; `routePaths`, `ticketPath`.
- Produces: `parseTicketFilters(search: URLSearchParams): TicketFilters`, `ticketFiltersToSearch(filters: TicketFilters): URLSearchParams`; `@/pages/tickets`: `TicketsLayout`, `TicketsIndexPage` (и `TicketPage` из Task 6).

- [ ] **Step 1: Тест `filters.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import { parseTicketFilters, ticketFiltersToSearch } from './filters'

describe('parseTicketFilters', () => {
  it('reads status and mine', () => {
    expect(parseTicketFilters(new URLSearchParams('status=NEW&mine=1'))).toEqual({
      status: 'NEW',
      mine: true,
    })
  })

  it('defaults to all active tickets', () => {
    expect(parseTicketFilters(new URLSearchParams(''))).toEqual({ status: null, mine: false })
  })

  it('drops values the list cannot filter by', () => {
    expect(parseTicketFilters(new URLSearchParams('status=CLOSED&mine=yes'))).toEqual({
      status: null,
      mine: false,
    })
  })
})

describe('ticketFiltersToSearch', () => {
  it('writes only non-default values', () => {
    expect(ticketFiltersToSearch({ status: 'WAITING_CLIENT', mine: true }).toString()).toBe(
      'status=WAITING_CLIENT&mine=1',
    )
    expect(ticketFiltersToSearch({ status: null, mine: false }).toString()).toBe('')
  })

  it('round-trips', () => {
    const filters = { status: 'IN_PROGRESS', mine: false } as const
    expect(parseTicketFilters(ticketFiltersToSearch(filters))).toEqual(filters)
  })
})
```

- [ ] **Step 2: Запустить — падает**

Run: `pnpm exec vitest run src/pages/tickets`
Expected: FAIL — не найден `./filters`.

- [ ] **Step 3: `lib/filters.ts`**

```ts
import type { ActiveTicketStatus, TicketFilters } from '@/entities/ticket'

const ACTIVE_STATUSES: readonly ActiveTicketStatus[] = ['NEW', 'IN_PROGRESS', 'WAITING_CLIENT']

function isActiveStatus(value: string | null): value is ActiveTicketStatus {
  return ACTIVE_STATUSES.includes(value as ActiveTicketStatus)
}

export function parseTicketFilters(search: URLSearchParams): TicketFilters {
  const status = search.get('status')
  return {
    status: isActiveStatus(status) ? status : null,
    mine: search.get('mine') === '1',
  }
}

export function ticketFiltersToSearch(filters: TicketFilters): URLSearchParams {
  const search = new URLSearchParams()
  if (filters.status) {
    search.set('status', filters.status)
  }
  if (filters.mine) {
    search.set('mine', '1')
  }
  return search
}
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/pages/tickets`
Expected: PASS (5 тестов).

- [ ] **Step 5: Каркас на всю высоту**

`widgets/app-shell/ui/AppShell.tsx`: внешний контейнер `flex min-h-dvh` → `flex h-dvh`; `<main className="flex-1 pb-[calc(3rem+env(safe-area-inset-bottom))] lg:pb-0">` → `<main className="flex min-h-0 flex-1 flex-col overflow-hidden pb-[calc(3rem+env(safe-area-inset-bottom))] lg:pb-0">`. В `SideLink` и `TabLink` убрать `end` у `NavLink` — «Обращения» должны подсвечиваться и на `/staff/tickets/:id`.

- [ ] **Step 6: UI списка**

`ui/TicketFiltersBar.tsx`:
```tsx
import { WifiOff } from 'lucide-react'
import type { ActiveTicketStatus, TicketFilters } from '@/entities/ticket'
import { useSocketStatus } from '@/shared/lib/ws'

const STATUS_OPTIONS: { value: ActiveTicketStatus | null; label: string }[] = [
  { value: null, label: 'Все' },
  { value: 'NEW', label: 'Новые' },
  { value: 'IN_PROGRESS', label: 'В работе' },
  { value: 'WAITING_CLIENT', label: 'Ждут ответа' },
]

interface TicketFiltersBarProps {
  filters: TicketFilters
  onChange: (filters: TicketFilters) => void
}

export function TicketFiltersBar({ filters, onChange }: TicketFiltersBarProps) {
  const online = useSocketStatus((state) => state.online)
  return (
    <div className="flex flex-col gap-2 border-b border-neutral-200 p-3 dark:border-neutral-800">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-lg font-semibold">Обращения</h1>
        {!online && (
          <span className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
            <WifiOff size={14} strokeWidth={2} />
            Нет связи
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {STATUS_OPTIONS.map((option) => (
          <button
            key={option.label}
            type="button"
            onClick={() => onChange({ ...filters, status: option.value })}
            className={`rounded-full px-3 py-1 text-sm transition-colors ${
              filters.status === option.value
                ? 'bg-brand text-white'
                : 'bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700'
            }`}
          >
            {option.label}
          </button>
        ))}
        <button
          type="button"
          onClick={() => onChange({ ...filters, mine: !filters.mine })}
          aria-pressed={filters.mine}
          className={`rounded-full px-3 py-1 text-sm transition-colors ${
            filters.mine
              ? 'bg-brand text-white'
              : 'bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700'
          }`}
        >
          Мои
        </button>
      </div>
    </div>
  )
}
```

`ui/TicketRow.tsx`:
```tsx
import { NavLink, useLocation } from 'react-router'
import {
  TicketStatusBadge,
  UrgentMark,
  ticketTypeLabels,
  type TicketListItem,
} from '@/entities/ticket'
import { ticketPath } from '@/shared/config'
import { formatRelativeTime } from '@/shared/lib/format'

export function TicketRow({ ticket }: { ticket: TicketListItem }) {
  const { search } = useLocation()
  const address = ticket.building
    ? `${ticket.building.address}${ticket.apartment ? `, кв. ${ticket.apartment}` : ''}`
    : null

  return (
    <NavLink
      to={{ pathname: ticketPath(ticket.id), search }}
      className={({ isActive }) =>
        `flex flex-col gap-1 border-b border-neutral-100 px-3 py-3 transition-colors dark:border-neutral-800/60 ${
          isActive ? 'bg-brand/10' : 'hover:bg-neutral-100 dark:hover:bg-neutral-900'
        }`
      }
    >
      <div className="flex items-center gap-2">
        {ticket.unread && (
          <span className="size-2 shrink-0 rounded-full bg-brand" aria-label="Непрочитано" />
        )}
        <span className="font-medium">№{ticket.id}</span>
        <span className="truncate text-sm text-neutral-500">
          {ticket.category?.title ?? ticketTypeLabels[ticket.type]}
        </span>
        {ticket.priority === 'URGENT' && <UrgentMark />}
        <span className="ml-auto shrink-0 text-xs text-neutral-500">
          {formatRelativeTime(ticket.created_at)}
        </span>
      </div>
      <p className="line-clamp-2 text-sm">{ticket.description}</p>
      <div className="flex items-center gap-2 text-xs text-neutral-500">
        <span className="truncate">
          {ticket.client.first_name}
          {address && ` · ${address}`}
        </span>
        <span className="ml-auto">
          <TicketStatusBadge status={ticket.status} />
        </span>
      </div>
    </NavLink>
  )
}
```

`ui/TicketList.tsx`:
```tsx
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
```

`ui/TicketsLayout.tsx`:
```tsx
import { Outlet, useMatch } from 'react-router'
import { routePaths } from '@/shared/config'
import { TicketList } from './TicketList'

export function TicketsLayout() {
  const hasTicket = useMatch(routePaths.ticket) !== null
  return (
    <div className="flex min-h-0 flex-1">
      <section
        className={`${hasTicket ? 'hidden lg:flex' : 'flex'} w-full shrink-0 flex-col border-neutral-200 lg:w-80 lg:border-r xl:w-96 dark:border-neutral-800`}
      >
        <TicketList />
      </section>
      <div className={`${hasTicket ? 'flex' : 'hidden lg:flex'} min-w-0 flex-1`}>
        <Outlet />
      </div>
    </div>
  )
}
```

`ui/TicketsIndexPage.tsx`:
```tsx
import { MessagesSquare } from 'lucide-react'
import { EmptyState } from '@/shared/ui/empty-state'

export function TicketsIndexPage() {
  return (
    <EmptyState
      icon={<MessagesSquare size={48} strokeWidth={1.5} />}
      title="Выберите обращение"
      text="Слева — активные обращения жильцов. Новые появляются автоматически."
    />
  )
}
```

`index.ts`:
```ts
export { TicketsIndexPage } from './ui/TicketsIndexPage'
export { TicketsLayout } from './ui/TicketsLayout'
```

- [ ] **Step 7: Роутер**

Удалить `src/pages/staff-home/`. В `router.tsx` импорт `StaffHomePage` заменить на `import { TicketsIndexPage, TicketsLayout } from '@/pages/tickets'`, дети ветки `staff`:
```tsx
        children: [
          {
            element: <TicketsLayout />,
            children: [{ index: true, element: <TicketsIndexPage /> }],
          },
        ],
```

- [ ] **Step 8: Проверка, ручной осмотр, коммит**

Run: `bash scripts/check.sh`
Expected: `all checks passed`.

Ручной осмотр (бэкенд с сидами, `pnpm dev`, `http://127.0.0.1:5173`, Игорь): список демо-обращений, фильтры меняют URL и список, «Мои» работает, перезагрузка сохраняет фильтр.

```bash
git add -A frontend/src
git commit -m "feat(web): add ticket list with filters"
```

---

### Task 6: Экран обращения и чат

**Files:**
- Create: `frontend/src/pages/tickets/{lib/message-rules.ts, api/send-message.ts, api/mark-read.ts, model/use-send-message.ts, model/use-mark-read.ts, ui/TicketPage.tsx, ui/TicketHeader.tsx, ui/Chat.tsx, ui/Composer.tsx}`
- Modify: `frontend/src/pages/tickets/index.ts`, `frontend/src/app/routes/router.tsx`
- Test: `frontend/src/pages/tickets/lib/message-rules.test.ts`

**Interfaces:**
- Consumes: `useTicket`, `TicketDetail`, `TicketStatusBadge`, `UrgentMark`, `ticketTypeLabels`, `invalidateTicketLists` (`@/entities/ticket`); `useMessages`, `appendMessage`, `MessageBubble`, `Message` (`@/entities/message`); `useMediaQuery`, `breakpoints`; `EmptyState`; `api`, `unwrap`, `isApiError`.
- Produces: `MESSAGE_TEXT_LIMIT = 3000`, `validateMessage(text: string, files: AttachmentLike[]): string | null`, `hasContent(text: string, files: unknown[]): boolean`, `type AttachmentLike = { name: string; type: string; size: number }`; `@/pages/tickets`: `TicketPage`; внутри слайса — `TicketHeader({ ticket, tab?, onTabChange?, onOpenDetails? })`, `Chat({ ticket })`.

- [ ] **Step 1: Тест `message-rules.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import { hasContent, validateMessage } from './message-rules'

const MB = 1024 * 1024
const photo = (name = 'a.jpg', size = MB) => ({ name, type: 'image/jpeg', size })
const pdf = (name = 'act.pdf', size = MB) => ({ name, type: 'application/pdf', size })

describe('hasContent', () => {
  it('needs text that is not only spaces, or files', () => {
    expect(hasContent('   ', [])).toBe(false)
    expect(hasContent(' Идём ', [])).toBe(true)
    expect(hasContent('', [photo()])).toBe(true)
  })
})

describe('validateMessage', () => {
  it('accepts text with up to 10 photos', () => {
    expect(validateMessage('Готово', Array.from({ length: 10 }, (_, i) => photo(`${i}.jpg`)))).toBeNull()
  })

  it('accepts a single document', () => {
    expect(validateMessage('', [pdf()])).toBeNull()
  })

  it('rejects text over 3000 characters', () => {
    expect(validateMessage('а'.repeat(3001), [])).toBe('Сообщение длиннее 3000 символов')
  })

  it('rejects more than 10 photos', () => {
    const photos = Array.from({ length: 11 }, (_, i) => photo(`${i}.jpg`))
    expect(validateMessage('', photos)).toBe('Можно приложить не больше 10 фото')
  })

  it('rejects a document together with other files', () => {
    expect(validateMessage('', [pdf(), photo()])).toBe(
      'Документ отправляется один, без других файлов',
    )
  })

  it('rejects files over 20 MB', () => {
    expect(validateMessage('', [photo('big.jpg', 25 * MB)])).toBe('Файл «big.jpg» больше 20 МБ')
  })
})
```

- [ ] **Step 2: Запустить — падает**

Run: `pnpm exec vitest run src/pages/tickets/lib/message-rules.test.ts`
Expected: FAIL — не найден `./message-rules`.

- [ ] **Step 3: `lib/message-rules.ts`**

```ts
export const MESSAGE_TEXT_LIMIT = 3000
const MAX_PHOTOS = 10
const MAX_FILE_SIZE = 20 * 1024 * 1024

export interface AttachmentLike {
  name: string
  type: string
  size: number
}

export function hasContent(text: string, files: unknown[]): boolean {
  return text.trim() !== '' || files.length > 0
}

// Mirrors the backend limits so the user learns about them before sending.
export function validateMessage(text: string, files: AttachmentLike[]): string | null {
  if (text.length > MESSAGE_TEXT_LIMIT) {
    return `Сообщение длиннее ${MESSAGE_TEXT_LIMIT} символов`
  }
  if (files.length > 1 && files.some((file) => !file.type.startsWith('image/'))) {
    return 'Документ отправляется один, без других файлов'
  }
  if (files.length > MAX_PHOTOS) {
    return `Можно приложить не больше ${MAX_PHOTOS} фото`
  }
  const tooBig = files.find((file) => file.size > MAX_FILE_SIZE)
  if (tooBig) {
    return `Файл «${tooBig.name}» больше 20 МБ`
  }
  return null
}
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/pages/tickets/lib/message-rules.test.ts`
Expected: PASS (7 тестов). Порядок проверок важен: 11 фото — «не больше 10 фото», а не «документ».

- [ ] **Step 5: API и модели**

`api/send-message.ts`:
```ts
import { api, unwrap } from '@/shared/api'

export function sendMessage(ticketId: number, text: string, files: File[]) {
  const form = new FormData()
  const trimmed = text.trim()
  if (trimmed) {
    form.append('text', trimmed)
  }
  for (const file of files) {
    form.append('files', file)
  }
  return unwrap(
    api.POST('/api/v1/staff/tickets/{ticket_id}/messages', {
      params: { path: { ticket_id: ticketId } },
      // The schema types multipart fields as strings; the real body is the FormData.
      body: {} as never,
      bodySerializer: () => form,
    }),
  )
}
```

`api/mark-read.ts`:
```ts
import { api, unwrap } from '@/shared/api'

export function markRead(ticketId: number) {
  return unwrap(
    api.POST('/api/v1/staff/tickets/{ticket_id}/read', { params: { path: { ticket_id: ticketId } } }),
  )
}
```

`model/use-send-message.ts`:
```ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { appendMessage } from '@/entities/message'
import { sendMessage } from '../api/send-message'

export function useSendMessage(ticketId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ text, files }: { text: string; files: File[] }) =>
      sendMessage(ticketId, text, files),
    onSuccess: (message) => appendMessage(queryClient, message),
  })
}
```

`model/use-mark-read.ts`:
```ts
import { useMutation } from '@tanstack/react-query'
import { useCallback, useRef } from 'react'
import { markRead } from '../api/mark-read'

const MIN_INTERVAL = 1000

export function useMarkRead(ticketId: number): () => void {
  const { mutate } = useMutation({ mutationFn: () => markRead(ticketId) })
  const lastSent = useRef(0)
  return useCallback(() => {
    const now = Date.now()
    if (now - lastSent.current < MIN_INTERVAL) {
      return
    }
    lastSent.current = now
    mutate()
  }, [mutate])
}
```

- [ ] **Step 6: UI**

`ui/Composer.tsx`:
```tsx
import { Button, Textarea } from '@maxhub/max-ui'
import { Paperclip, SendHorizontal, X } from 'lucide-react'
import { useRef, useState, type KeyboardEvent } from 'react'
import { formatFileSize } from '@/shared/lib/format'
import { hasContent, MESSAGE_TEXT_LIMIT, validateMessage } from '../lib/message-rules'
import { useSendMessage } from '../model/use-send-message'

export function Composer({ ticketId }: { ticketId: number }) {
  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const fileInput = useRef<HTMLInputElement>(null)
  const send = useSendMessage(ticketId)

  const validationError = validateMessage(text, files)
  const canSend = hasContent(text, files) && validationError === null && !send.isPending

  const submit = () => {
    if (!canSend) {
      return
    }
    send.mutate(
      { text, files },
      {
        onSuccess: () => {
          setText('')
          setFiles([])
        },
      },
    )
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  const error = validationError ?? send.error?.message

  return (
    <div className="flex flex-col gap-2 border-t border-neutral-200 p-3 dark:border-neutral-800">
      {files.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${index}`}
              className="flex items-center gap-1 rounded-full bg-neutral-100 py-1 pr-1 pl-3 text-xs dark:bg-neutral-800"
            >
              <span className="max-w-40 truncate">{file.name}</span>
              <span className="text-neutral-500">{formatFileSize(file.size)}</span>
              <button
                type="button"
                aria-label={`Убрать ${file.name}`}
                className="rounded-full p-1 hover:bg-neutral-200 dark:hover:bg-neutral-700"
                onClick={() => setFiles(files.filter((_, i) => i !== index))}
              >
                <X size={12} strokeWidth={2} />
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex items-end gap-2">
        <button
          type="button"
          aria-label="Прикрепить файлы"
          disabled={send.isPending}
          className="rounded-full p-2 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800"
          onClick={() => fileInput.current?.click()}
        >
          <Paperclip size={20} strokeWidth={2} />
        </button>
        <input
          ref={fileInput}
          type="file"
          multiple
          hidden
          onChange={(event) => {
            setFiles([...files, ...Array.from(event.target.files ?? [])])
            event.target.value = ''
          }}
        />
        <Textarea
          value={text}
          rows={1}
          maxLength={MESSAGE_TEXT_LIMIT + 1}
          placeholder="Сообщение"
          disabled={send.isPending}
          className="max-h-40 min-w-0 flex-1 resize-none"
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
        />
        <Button
          aria-label="Отправить"
          size="medium"
          disabled={!canSend}
          loading={send.isPending}
          onClick={submit}
          iconBefore={<SendHorizontal size={20} strokeWidth={2} />}
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  )
}
```

`ui/Chat.tsx`:
```tsx
import { Button } from '@maxhub/max-ui'
import { MessageCircle } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useLayoutEffect, useRef } from 'react'
import { MessageBubble, useMessages } from '@/entities/message'
import type { TicketDetail } from '@/entities/ticket'
import { EmptyState } from '@/shared/ui/empty-state'
import { useMarkRead } from '../model/use-mark-read'
import { Composer } from './Composer'

const NEAR_BOTTOM = 80

export function Chat({ ticket }: { ticket: TicketDetail }) {
  const messages = useMessages(ticket.id)
  const markRead = useMarkRead(ticket.id)
  const scroller = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)
  const items = messages.data ?? []
  const lastClientMessageId = items.findLast((m) => m.sender_type === 'CLIENT')?.id

  // The chat is on screen: mark it read when it opens and when the client writes again.
  useEffect(() => {
    markRead()
  }, [ticket.id, lastClientMessageId, markRead])

  useLayoutEffect(() => {
    const element = scroller.current
    if (element && stickToBottom.current) {
      element.scrollTop = element.scrollHeight
    }
  }, [items.length, ticket.id])

  const closed = ticket.status === 'CLOSED' || ticket.status === 'REJECTED'

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        ref={scroller}
        className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto bg-neutral-50 p-4 dark:bg-neutral-950"
        onScroll={(event) => {
          const element = event.currentTarget
          stickToBottom.current =
            element.scrollHeight - element.scrollTop - element.clientHeight < NEAR_BOTTOM
        }}
      >
        {messages.isPending && (
          <div className="m-auto text-sm text-neutral-500">Загрузка…</div>
        )}
        {messages.isError && (
          <EmptyState
            icon={<MessageCircle size={48} strokeWidth={1.5} />}
            title="Не удалось загрузить переписку"
            text={messages.error.message}
            action={<Button onClick={() => void messages.refetch()}>Повторить</Button>}
          />
        )}
        {messages.isSuccess && items.length === 0 && (
          <EmptyState
            icon={<MessageCircle size={48} strokeWidth={1.5} />}
            title="Сообщений пока нет"
            text="Напишите жильцу — ответ придёт ему в Max."
          />
        )}
        <AnimatePresence initial={false}>
          {items.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <MessageBubble message={message} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      {closed ? (
        <div className="border-t border-neutral-200 p-4 text-center text-sm text-neutral-500 dark:border-neutral-800">
          Обращение закрыто — писать в него нельзя
        </div>
      ) : (
        <Composer ticketId={ticket.id} />
      )}
    </div>
  )
}
```

`ui/TicketHeader.tsx`:
```tsx
import { ChevronLeft, PanelRight } from 'lucide-react'
import { Link, useLocation } from 'react-router'
import { TicketStatusBadge, UrgentMark, ticketTypeLabels, type TicketDetail } from '@/entities/ticket'
import { routePaths } from '@/shared/config'

export type TicketTab = 'chat' | 'details'

interface TicketHeaderProps {
  ticket: TicketDetail
  tab: TicketTab
  onTabChange: (tab: TicketTab) => void
  // Shown between lg and xl, where details live in a drawer.
  onOpenDetails: () => void
}

export function TicketHeader({ ticket, tab, onTabChange, onOpenDetails }: TicketHeaderProps) {
  const { search } = useLocation()
  return (
    <header className="border-b border-neutral-200 dark:border-neutral-800">
      <div className="flex items-center gap-2 px-3 py-2">
        <Link
          to={{ pathname: routePaths.staff, search }}
          aria-label="К списку"
          className="-ml-1 rounded-full p-1 hover:bg-neutral-100 lg:hidden dark:hover:bg-neutral-800"
        >
          <ChevronLeft size={20} strokeWidth={2} />
        </Link>
        <span className="font-semibold">№{ticket.id}</span>
        <span className="truncate text-sm text-neutral-500">
          {ticket.category?.title ?? ticketTypeLabels[ticket.type]}
        </span>
        {ticket.priority === 'URGENT' && <UrgentMark />}
        <span className="ml-auto">
          <TicketStatusBadge status={ticket.status} />
        </span>
        <button
          type="button"
          aria-label="Детали"
          onClick={onOpenDetails}
          className="hidden rounded-full p-1 hover:bg-neutral-100 lg:inline-flex xl:hidden dark:hover:bg-neutral-800"
        >
          <PanelRight size={20} strokeWidth={2} />
        </button>
      </div>
      <div className="flex lg:hidden" role="tablist">
        {(['chat', 'details'] as const).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={tab === value}
            onClick={() => onTabChange(value)}
            className={`flex-1 border-b-2 py-2 text-sm ${
              tab === value ? 'border-brand font-medium text-brand' : 'border-transparent text-neutral-500'
            }`}
          >
            {value === 'chat' ? 'Чат' : 'Детали'}
          </button>
        ))}
      </div>
    </header>
  )
}
```

`ui/TicketPage.tsx` (детали добавляются в Task 7; здесь — чат и заглушка на месте деталей):
```tsx
import { Button } from '@maxhub/max-ui'
import { FileQuestion, SearchX } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { useTicket } from '@/entities/ticket'
import { isApiError } from '@/shared/api'
import { routePaths } from '@/shared/config'
import { breakpoints, useMediaQuery } from '@/shared/lib/media-query'
import { EmptyState } from '@/shared/ui/empty-state'
import { Chat } from './Chat'
import { TicketHeader, type TicketTab } from './TicketHeader'

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
  const isLg = useMediaQuery(breakpoints.lg)
  const [tab, setTab] = useState<TicketTab>('chat')
  const [, setDetailsOpen] = useState(false)

  if (ticket.isPending) {
    return <div className="m-auto text-sm text-neutral-500">Загрузка…</div>
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

  const showChat = isLg || tab === 'chat'
  return (
    <div className="flex min-w-0 flex-1">
      <section className="flex min-w-0 flex-1 flex-col">
        <TicketHeader
          ticket={ticket.data}
          tab={tab}
          onTabChange={setTab}
          onOpenDetails={() => setDetailsOpen(true)}
        />
        {showChat ? <Chat ticket={ticket.data} /> : null}
      </section>
    </div>
  )
}

export function TicketPage() {
  const { id } = useParams()
  const ticketId = parseTicketId(id)
  return ticketId === null ? <TicketNotFound /> : <TicketView key={ticketId} id={ticketId} />
}
```

`index.ts` — добавить `export { TicketPage } from './ui/TicketPage'`.

`router.tsx` — в детях `TicketsLayout` добавить `{ path: routePaths.ticket, element: <TicketPage /> }` (импорт `TicketPage` из `@/pages/tickets`).

- [ ] **Step 7: Проверка, ручной осмотр, коммит**

Run: `bash scripts/check.sh`
Expected: `all checks passed`. Если `Button` без `children` с `iconBefore` рендерится некрасиво — оставить как есть и записать в журнал (правка вида — Task 10). Если `Array.prototype.findLast` не типизируется — `lib` в `tsconfig.app.json` уже `ES2023`, должно работать.

Ручной осмотр: открыть обращение; отправить текст; отправить фото; в Swagger или через бота написать от клиента — сообщение появляется без перезагрузки; точка непрочитанного в списке пропадает при открытии.

```bash
git add -A frontend/src
git commit -m "feat(web): add ticket chat with attachments and read marks"
```

---

### Task 7: Детали, статусы, отклонение

**Files:**
- Create: `frontend/src/pages/tickets/{lib/status-actions.ts, api/change-status.ts, model/use-change-status.ts, ui/TicketDetails.tsx, ui/StatusActions.tsx, ui/RejectDialog.tsx, ui/DetailsDrawer.tsx}`
- Modify: `frontend/src/pages/tickets/ui/TicketPage.tsx`
- Test: `frontend/src/pages/tickets/lib/status-actions.test.ts`

**Interfaces:**
- Consumes: `TicketDetail`, `TicketStatus`, `statusLabels`, `ticketTypeLabels`, `ticketKeys`, `invalidateTicketLists`, `invalidateTicket` (`@/entities/ticket`); `formatDateTime` (`@/shared/lib/format`).
- Produces: `statusActionLabel(from: TicketStatus, to: TicketStatus): string`, `validateRejectReason(reason: string): string | null`; `TicketDetails({ ticket })`, `DetailsDrawer({ open, onClose, children })`.

- [ ] **Step 1: Тест `status-actions.test.ts`**

```ts
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
```

- [ ] **Step 2: Запустить — падает**

Run: `pnpm exec vitest run src/pages/tickets/lib/status-actions.test.ts`
Expected: FAIL — не найден `./status-actions`.

- [ ] **Step 3: `lib/status-actions.ts`**

```ts
import type { TicketStatus } from '@/entities/ticket'

const REASON_LIMIT = 3000

export function statusActionLabel(from: TicketStatus, to: TicketStatus): string {
  switch (to) {
    case 'WAITING_CLIENT':
      return 'Нужен ответ клиента'
    case 'CLOSED':
      return 'Закрыть'
    case 'REJECTED':
      return 'Отклонить'
    case 'IN_PROGRESS':
      if (from === 'NEW') {
        return 'Взять в работу'
      }
      return from === 'CLOSED' || from === 'REJECTED' ? 'Переоткрыть' : 'Вернуть в работу'
    case 'NEW':
      return 'Вернуть в новые'
  }
}

export function validateRejectReason(reason: string): string | null {
  if (reason.trim() === '') {
    return 'Укажите причину — её увидит жилец'
  }
  if (reason.length > REASON_LIMIT) {
    return `Причина длиннее ${REASON_LIMIT} символов`
  }
  return null
}
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/pages/tickets/lib/status-actions.test.ts`
Expected: PASS (11 тестов).

- [ ] **Step 5: API и модель**

`api/change-status.ts`:
```ts
import type { TicketStatus } from '@/entities/ticket'
import { api, unwrap } from '@/shared/api'

export function changeStatus(ticketId: number, status: TicketStatus, comment: string | null) {
  return unwrap(
    api.POST('/api/v1/staff/tickets/{ticket_id}/status', {
      params: { path: { ticket_id: ticketId } },
      body: { status, comment },
    }),
  )
}
```

`model/use-change-status.ts`:
```ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  invalidateTicket,
  invalidateTicketLists,
  ticketKeys,
  type TicketStatus,
} from '@/entities/ticket'
import { changeStatus } from '../api/change-status'

export function useChangeStatus(ticketId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ status, comment }: { status: TicketStatus; comment: string | null }) =>
      changeStatus(ticketId, status, comment),
    onSuccess: (ticket) => {
      queryClient.setQueryData(ticketKeys.detail(ticketId), ticket)
      void invalidateTicketLists(queryClient)
    },
    // Someone else may have changed the ticket first: show the fresh state.
    onError: () => void invalidateTicket(queryClient, ticketId),
  })
}
```

- [ ] **Step 6: UI**

`ui/RejectDialog.tsx`:
```tsx
import { Button, Textarea } from '@maxhub/max-ui'
import { useEffect, useRef, useState } from 'react'
import { validateRejectReason } from '../lib/status-actions'

interface RejectDialogProps {
  open: boolean
  pending: boolean
  onClose: () => void
  onConfirm: (reason: string) => void
}

export function RejectDialog({ open, pending, onClose, onConfirm }: RejectDialogProps) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [reason, setReason] = useState('')
  const [touched, setTouched] = useState(false)
  const error = validateRejectReason(reason)

  useEffect(() => {
    const element = dialog.current
    if (open && !element?.open) {
      element?.showModal()
    }
    if (!open && element?.open) {
      element.close()
    }
  }, [open])

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      className="m-auto w-full max-w-md rounded-2xl bg-white p-0 text-neutral-900 backdrop:bg-black/40 dark:bg-neutral-900 dark:text-neutral-100"
    >
      <form
        method="dialog"
        className="flex flex-col gap-3 p-5"
        onSubmit={(event) => {
          event.preventDefault()
          setTouched(true)
          if (error === null) {
            onConfirm(reason.trim())
          }
        }}
      >
        <h2 className="text-lg font-semibold">Отклонить обращение</h2>
        <p className="text-sm text-neutral-500">Причину увидит жилец.</p>
        <Textarea
          value={reason}
          rows={4}
          autoFocus
          placeholder="Причина"
          onChange={(event) => setReason(event.target.value)}
        />
        {touched && error && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" variant="destructive" loading={pending}>
            Отклонить
          </Button>
        </div>
      </form>
    </dialog>
  )
}
```

`ui/StatusActions.tsx`:
```tsx
import { Button } from '@maxhub/max-ui'
import { useState } from 'react'
import type { TicketDetail, TicketStatus } from '@/entities/ticket'
import { statusActionLabel } from '../lib/status-actions'
import { useChangeStatus } from '../model/use-change-status'
import { RejectDialog } from './RejectDialog'

export function StatusActions({ ticket }: { ticket: TicketDetail }) {
  const change = useChangeStatus(ticket.id)
  const [rejecting, setRejecting] = useState(false)

  if (ticket.allowed_statuses.length === 0) {
    return null
  }

  const run = (status: TicketStatus) => {
    if (status === 'REJECTED') {
      setRejecting(true)
      return
    }
    change.mutate({ status, comment: null })
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {ticket.allowed_statuses.map((status) => (
          <Button
            key={status}
            size="small"
            variant={status === 'REJECTED' ? 'secondary' : 'primary'}
            disabled={change.isPending}
            onClick={() => run(status)}
          >
            {statusActionLabel(ticket.status, status)}
          </Button>
        ))}
      </div>
      {change.error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {change.error.message}
        </p>
      )}
      <RejectDialog
        open={rejecting}
        pending={change.isPending}
        onClose={() => setRejecting(false)}
        onConfirm={(reason) =>
          change.mutate(
            { status: 'REJECTED', comment: reason },
            { onSuccess: () => setRejecting(false) },
          )
        }
      />
    </div>
  )
}
```

`ui/TicketDetails.tsx`:
```tsx
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
                  className={value <= (ticket.rating ?? 0) ? 'fill-amber-400 text-amber-400' : 'text-neutral-300'}
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
```

`ui/DetailsDrawer.tsx`:
```tsx
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'

interface DetailsDrawerProps {
  open: boolean
  onClose: () => void
  children: ReactNode
}

export function DetailsDrawer({ open, onClose, children }: DetailsDrawerProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-black/30"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed inset-y-0 right-0 z-50 w-96 max-w-full overflow-y-auto bg-white shadow-xl dark:bg-neutral-900"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'tween', duration: 0.2 }}
          >
            <button
              type="button"
              aria-label="Закрыть"
              onClick={onClose}
              className="absolute top-3 right-3 rounded-full p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              <X size={20} strokeWidth={2} />
            </button>
            {children}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
```

`ui/TicketPage.tsx` — в `TicketView`:
- `const isXl = useMediaQuery(breakpoints.xl)` и `const [detailsOpen, setDetailsOpen] = useState(false)` (вместо `const [, setDetailsOpen]`);
- тело после заголовка: `{showChat ? <Chat ticket={ticket.data} /> : <div className="min-h-0 flex-1 overflow-y-auto"><TicketDetails ticket={ticket.data} /></div>}`;
- после `</section>`:
```tsx
      {isXl && (
        <aside className="w-80 shrink-0 overflow-y-auto border-l border-neutral-200 dark:border-neutral-800">
          <TicketDetails ticket={ticket.data} />
        </aside>
      )}
      <DetailsDrawer open={isLg && !isXl && detailsOpen} onClose={() => setDetailsOpen(false)}>
        <TicketDetails ticket={ticket.data} />
      </DetailsDrawer>
```
- импорты `TicketDetails`, `DetailsDrawer`.

- [ ] **Step 7: Проверка, ручной осмотр, коммит**

Run: `bash scripts/check.sh`
Expected: `all checks passed`.

Ручной осмотр: у нового — «Взять в работу» / «Отклонить»; взять → «В работе», в истории запись; «Нужен ответ клиента»; «Закрыть» → поле ввода заменено надписью; «Отклонить» без причины — ошибка, с причиной — «Отклонено»; у админа (Анна) — «Переоткрыть» у закрытого (закрытые в списке не видны — открыть по URL `/staff/tickets/<id>`). Ширины 1100px (drawer) и 1400px (три колонки).

```bash
git add -A frontend/src
git commit -m "feat(web): add ticket details and status actions"
```

---

### Task 8: Кнопка «Открыть» из Max

**Files:**
- Create: `frontend/src/app/routes/deep-link.ts`
- Modify: `frontend/src/app/routes/RoleRedirect.tsx`
- Test: `frontend/src/app/routes/deep-link.test.ts`

**Interfaces:**
- Consumes: `getStartParam` (`@/shared/lib/max-bridge`), `ticketPath` (`@/shared/config`), `isStaff` (`@/entities/user`).
- Produces: `ticketPathFromStartParam(param: string | null): string | null`, `takeStartPath(): string | null`, `forgetStartPath(): void`.

- [ ] **Step 1: Тест `deep-link.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import { ticketPathFromStartParam } from './deep-link'

describe('ticketPathFromStartParam', () => {
  it('opens the ticket from the "Открыть" button', () => {
    expect(ticketPathFromStartParam('ticket_1042')).toBe('/staff/tickets/1042')
  })

  it.each([null, '', 'ticket_', 'ticket_abc', 'ticket_-1', 'ticket_0', 'ticket_1.5', 'foo', 'ticket_12x'])(
    'ignores %j',
    (param) => {
      expect(ticketPathFromStartParam(param)).toBeNull()
    },
  )
})
```

- [ ] **Step 2: Запустить — падает**

Run: `pnpm exec vitest run src/app/routes/deep-link.test.ts`
Expected: FAIL — не найден `./deep-link`.

- [ ] **Step 3: `deep-link.ts`**

```ts
import { ticketPath } from '@/shared/config'
import { getStartParam } from '@/shared/lib/max-bridge'

const TICKET_PARAM = /^ticket_([1-9]\d*)$/

export function ticketPathFromStartParam(param: string | null): string | null {
  const match = param ? TICKET_PARAM.exec(param) : null
  if (!match) {
    return null
  }
  const id = Number(match[1])
  return Number.isSafeInteger(id) ? ticketPath(id) : null
}

// The start param belongs to this page load only: after the first redirect "/" goes home again.
let startPath = ticketPathFromStartParam(getStartParam())

export function takeStartPath(): string | null {
  return startPath
}

export function forgetStartPath(): void {
  startPath = null
}
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/app/routes/deep-link.test.ts`
Expected: PASS (10 тестов).

- [ ] **Step 5: `RoleRedirect.tsx`**

```tsx
import { useEffect } from 'react'
import { Navigate } from 'react-router'
import { useMe } from '@/entities/session'
import { isStaff } from '@/entities/user'
import { forgetStartPath, takeStartPath } from './deep-link'
import { homePathFor } from './home-path'

export function RoleRedirect() {
  const { data: user } = useMe()

  // Forget after commit, not during render: StrictMode renders twice.
  useEffect(() => forgetStartPath(), [])

  if (!user) {
    return null
  }
  const startPath = isStaff(user) ? takeStartPath() : null
  return <Navigate to={startPath ?? homePathFor(user)} replace />
}
```

- [ ] **Step 6: Проверка и коммит**

Run: `bash scripts/check.sh`
Expected: `all checks passed`.

Вручную в браузере это не проверить: `window.WebApp` задаёт только Max. Логику покрывают тесты, живая проверка — пункт Ф0.1.

```bash
git add frontend/src/app/routes
git commit -m "feat(web): open the ticket from the max notification button"
```

---

### Task 9: Lottie-анимации (шаг согласования с пользователем)

**Files:**
- Create: `frontend/src/shared/ui/lottie/{LottieAnimation.tsx, index.ts, animations/*.lottie}`
- Modify: `pages/tickets/ui/{TicketList.tsx, TicketsIndexPage.tsx, Chat.tsx, Composer.tsx, TicketDetails.tsx}`

**Interfaces:**
- Produces: `@/shared/ui/lottie`: `LottieAnimation({ src: string, loop?: boolean, className?: string, onComplete?: () => void })`, `animations = { emptyList, selectTicket, emptyChat, sent, closed }` (URL-ы файлов).

- [ ] **Step 1: Подбор анимаций**

Найти на lottiefiles.com (бесплатные, Lottie Simple License) по одной анимации: пустой ящик/список; выбор элемента/стрелка; пустой чат/облачко; «отправлено» (самолётик или галочка, ≤1 с); «закрыто/готово» (галочка, ≤1,5 с). Спокойная палитра, без текста внутри анимации, лёгкие (< 100 КБ).

- [ ] **Step 2: ОСТАНОВКА — согласовать с пользователем**

Показать пользователю список: название, ссылка на страницу анимации на LottieFiles, где будет использоваться. Дождаться ответа. Замены — повторить Step 1 для отвергнутых. **Без согласия анимации не вставлять.**

- [ ] **Step 3: Скачать согласованные**

Скачать `.lottie` (или `.json`) в `src/shared/ui/lottie/animations/` с именами `empty-list.lottie`, `select-ticket.lottie`, `empty-chat.lottie`, `sent.lottie`, `closed.lottie`. Если скачать автоматически нельзя (нужен вход на сайт) — попросить пользователя положить файлы в этот каталог и продолжить после.

- [ ] **Step 4: `LottieAnimation`**

`LottieAnimation.tsx`:
```tsx
import { useReducedMotion } from 'framer-motion'
import { lazy, Suspense } from 'react'

const DotLottieReact = lazy(() =>
  import('@lottiefiles/dotlottie-react').then((module) => ({ default: module.DotLottieReact })),
)

interface LottieAnimationProps {
  src: string
  loop?: boolean
  className?: string
  onComplete?: () => void
}

export function LottieAnimation({ src, loop = false, className, onComplete }: LottieAnimationProps) {
  // Reduced motion: the player shows the first frame and does not play.
  const reduced = useReducedMotion() ?? false
  return (
    <Suspense fallback={<div className={className} />}>
      <DotLottieReact
        src={src}
        autoplay={!reduced}
        loop={loop && !reduced}
        className={className}
        dotLottieRefCallback={(player) => {
          if (player && onComplete) {
            player.addEventListener('complete', onComplete)
          }
        }}
      />
    </Suspense>
  )
}
```

`index.ts`:
```ts
import closed from './animations/closed.lottie?url'
import emptyChat from './animations/empty-chat.lottie?url'
import emptyList from './animations/empty-list.lottie?url'
import selectTicket from './animations/select-ticket.lottie?url'
import sent from './animations/sent.lottie?url'

export const animations = { emptyList, selectTicket, emptyChat, sent, closed }
export { LottieAnimation } from './LottieAnimation'
```
Типы для `*?url` уже даёт `vite/client`. Если согласованы `.json`-файлы — импортировать так же, с `?url`.

- [ ] **Step 5: Подключить**

- `TicketList`: у «Обращений нет» — `animation={<LottieAnimation src={animations.emptyList} loop className="size-32" />}`.
- `TicketsIndexPage`: `animation={<LottieAnimation src={animations.selectTicket} loop className="size-32" />}`.
- `Chat`: у «Сообщений пока нет» — `animation={<LottieAnimation src={animations.emptyChat} loop className="size-32" />}`.
- `Composer`: `const [justSent, setJustSent] = useState(false)`; в `onSuccess` отправки — `setJustSent(true)`; поверх кнопки отправки (обёртка `relative`) при `justSent` — `<LottieAnimation src={animations.sent} className="pointer-events-none absolute inset-0 -m-3" onComplete={() => setJustSent(false)} />`.
- `StatusActions`: `const [justClosed, setJustClosed] = useState(false)`; при успешном переходе в `CLOSED` — `setJustClosed(true)`; рендер оверлея `fixed inset-0 z-50 flex items-center justify-center pointer-events-none` с `<LottieAnimation src={animations.closed} className="size-48" onComplete={() => setJustClosed(false)} />`.

- [ ] **Step 6: Проверка и коммит**

Run: `bash scripts/check.sh`
Expected: `all checks passed`; в сборке плеер — отдельный чанк (в выводе `vite build` появится `dotlottie`-чанк).

Ручной осмотр: анимации играют; при эмуляции reduced motion (DevTools → Rendering) — статичный кадр.

```bash
git add -A frontend/src
git commit -m "feat(web): add lottie animations to empty and success states"
```

---

### Task 10: Ручная проверка, документация

**Files:**
- Modify: `docs/plan.md`, `docs/architecture.md`

- [ ] **Step 1: Чек-лист из спека**

Бэкенд с сидами, `pnpm dev`, `http://127.0.0.1:5173`. Пройти все 11 пунктов раздела «Проверка (ручная)» спека. Сообщения от клиента — через Swagger нельзя (клиент пишет только боту); если бот недоступен, пункт 6 проверить вторым окном панели: ответ сотрудника из окна A должен появиться в окне B через `message_created`. Любой провал — исправить через superpowers:systematic-debugging, затем повторить `check.sh` и пункт.

- [ ] **Step 2: `docs/plan.md`**

Строки Ф2, Ф3, Ф4 отметить `[x]`, к Ф2 дописать: «Фильтры по дому и категории — после справочников в API».

- [ ] **Step 3: `docs/architecture.md`, раздел «Frontend»**

В дерево `frontend/src/` добавить: `pages/tickets` — список, обращение, чат, статусы; `entities/ticket`, `entities/message`; `shared/lib/ws`, `shared/lib/format`, `shared/lib/media-query`, `shared/ui/{empty-state,lottie}`; `app/realtime`. `features/` оставить как есть. После абзаца «Тема» добавить:
```markdown
Реалтайм: `app/realtime` держит WebSocket для сотрудника. `message_created` дописывает сообщение в кэш чата (дубли по `id` отбрасываются), `ticket_created`/`ticket_updated` перезапрашивают списки и карточку, после переподключения перечитывается всё. Закрытие `4401` — выход, `4403` — без переподключения.

Раскладка обращений: телефон — список и обращение по очереди (вкладки «Чат» / «Детали»); от `lg` — список | чат, детали в выезжающей панели; от `xl` — три колонки.
```

- [ ] **Step 4: Финальная проверка и коммит**

Run: `cd frontend && bash scripts/check.sh`
Expected: `all checks passed`.

```bash
git add docs/plan.md docs/architecture.md
git commit -m "docs: record tickets, chat and realtime in the frontend"
```
