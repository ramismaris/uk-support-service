# Фронтенд: фундамент (Ф0 + Ф1) — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SPA в `frontend/`: вход (`initData` в Max, dev-вход в браузере), адаптивный каркас с навигацией по ролям, светлая/тёмная тема, проверка `check.sh`.

**Architecture:** Feature-Sliced Design 2.x (`app → pages → widgets → features → entities → shared`), контроль — Steiger. Серверное состояние — TanStack Query поверх типизированного `openapi-fetch`-клиента, типы генерируются из `backend/openapi.json`. Токен — Zustand с `persist`; пользователь — только в кэше Query (`['me']`). Состояние входа вычисляет чистая функция `resolveSessionState`, компонент `SessionGate` её рендерит.

**Tech Stack:** Vite, React 19, TypeScript strict, Tailwind CSS v4, `@maxhub/max-ui`, framer-motion, React Router v7, TanStack Query v5, Zustand, openapi-typescript, openapi-fetch, pnpm, ESLint, Prettier, Steiger, Vitest + jsdom.

**Spec:** [docs/superpowers/specs/2026-09-26-frontend-foundation-design.md](../specs/2026-09-26-frontend-foundation-design.md)

## Global Constraints

- Все команды фронтенда — из каталога `frontend/`; пакетный менеджер — только pnpm.
- Код, идентификаторы, комментарии — на английском; тексты интерфейса — на русском.
- FSD: импорт только в нижележащие слои; кросс-импорт слайсов одного слоя запрещён; снаружи слайса — только через его `index.ts`; внутри слайса — относительные импорты; между слайсами — через алиас `@/`.
- В `app` и `shared` нет слайсов, только сегменты. Сегмента `ui` в `app` нет. Имена сегментов — по назначению (`ui`, `model`, `api`, `lib`, `config`), не `components`/`hooks`/`types`/`utils`.
- Если Steiger ругается и правило нельзя удовлетворить без нарушения спека (например, `fsd/insignificant-slice`) — **остановиться и спросить пользователя**, правила не отключать самостоятельно.
- `src/shared/api/schema.d.ts` — только генерация (`pnpm gen:api`), руками не править.
- Коммиты: Conventional Commits, область `web` (или `docs`), **только заголовок — без тела и без трейлеров `Co-Authored-By`** (правило `AGENTS.md`).
- Ветка: `feat/frontend-foundation`, создаётся от `docs/frontend-foundation-spec`. В `main` не вливать — вливает человек.
- Если API библиотеки расходится с кодом в плане (проп Max UI, экспорт) — сверить с `node_modules/<pkg>` и адаптировать минимально; если расхождение меняет поведение — остановиться и спросить.
- Бэкенд для ручной проверки: `backend/` → `cp .env.template .env` (там `DEV_AUTH=true`, `BOT_MODE=off`) → `docker compose up -d --build` → `docker compose exec api python scripts/seed.py`.

## Review Focus

- Протухший токен в localStorage (БД пересоздана) → `/me` отвечает 401 → пользователь попадает на `/login`, без бесконечного цикла. Тесты: Task 2 (`authMiddleware` на 401), Task 7 (`resolveSessionState`: token + 401 → loading, затем без токена → unauthenticated).
- Заблокированный пользователь (403 на `/me` или `/auth/max`) → экран «Доступ ограничен», без повторов запроса. Тесты: Task 2 (`shouldRetry` не повторяет 4xx), Task 7 (`blocked`).
- Бэкенд недоступен или отвечает 500 при живом токене → экран «Не удалось войти» с «Повторить», токен **не** сбрасывается. Тест: Task 7 (`error` для 500 и сетевой ошибки).
- Клиент открывает `/staff` напрямую (и сотрудник — `/client`) → редирект в свою ветку. Тесты: Task 4 (`isStaff`/`isClient`), Task 7 (`homePathFor`).
- Dev-вход с пустым, нечисловым или несуществующим `max_user_id` → кнопка неактивна / видно сообщение бэкенда «Пользователь не найден». Тесты: Task 5 (`parseMaxUserId`), Task 2 (`unwrap` поднимает `detail` в сообщение).

---

## Файловая карта

```
frontend/
├── index.html                                  скрипт Max, точка входа
├── vite.config.ts                              алиас @/, прокси /api, vitest
├── steiger.config.js                           правила FSD
├── .env.template                               VITE_DEV_AUTH
├── .prettierrc, .prettierignore
├── eslint.config.js                            шаблон Vite + prettier
├── scripts/check.sh                            полная проверка
└── src/
    ├── app/
    │   ├── entrypoint/main.tsx
    │   ├── providers/{AppProviders.tsx, ThemeProvider.tsx, api-session.ts}
    │   ├── routes/{router.tsx, SessionGate.tsx, RequireRole.tsx, RoleRedirect.tsx,
    │   │           session-state.ts(+test), home-path.ts(+test)}
    │   └── styles/index.css
    ├── pages/{login, staff-home, client-home, not-found}/{index.ts, ui/*Page.tsx}
    ├── widgets/app-shell/{index.ts, model/nav.ts(+test), ui/AppShell.tsx}
    ├── features/
    │   ├── auth-by-max/{index.ts, api/login-by-max.ts, model/use-login-by-max.ts}
    │   ├── auth-dev/{index.ts, api/dev-login.ts, config/seed-users.ts,
    │   │             lib/parse-max-user-id.ts(+test), model/use-dev-login.ts, ui/DevLoginForm.tsx}
    │   └── logout/{index.ts, api/logout.ts, model/use-logout.ts, ui/LogoutButton.tsx}
    ├── entities/
    │   ├── user/{index.ts, model/user.ts(+test)}
    │   └── session/{index.ts, api/me.ts, model/session-store.ts(+test), model/use-start-session.ts}
    └── shared/
        ├── api/{index.ts, schema.d.ts, client.ts(+test), errors.ts(+test), query-client.ts(+test)}
        ├── config/{index.ts, env.ts, routes.ts}
        ├── lib/max-bridge/{index.ts, types.ts, bridge.ts(+test)}
        ├── lib/color-scheme/{index.ts, use-color-scheme.ts}
        └── ui/{page-transition, splash-screen, status-screen}/{index.ts, *.tsx}
```

---

### Task 1: Скелет проекта, инструменты, проверка каскада стилей

**Files:**
- Create: `frontend/` (шаблон Vite), `frontend/vite.config.ts`, `frontend/steiger.config.js`, `frontend/.env.template`, `frontend/.prettierrc`, `frontend/.prettierignore`, `frontend/scripts/check.sh`, `frontend/src/app/entrypoint/main.tsx`, `frontend/src/app/styles/index.css`, `frontend/src/shared/api/schema.d.ts` (генерация)
- Modify: `frontend/index.html`, `frontend/package.json`, `frontend/tsconfig.app.json`, `frontend/eslint.config.js`
- Delete: `frontend/src/App.tsx`, `frontend/src/App.css`, `frontend/src/index.css`, `frontend/src/main.tsx`, `frontend/src/assets/`, `frontend/public/vite.svg`

**Interfaces:**
- Produces: алиас `@/` → `src/`; скрипты `pnpm gen:api`, `pnpm test`, `pnpm build`; `bash scripts/check.sh`; CSS-токен `--brand` / утилиты `bg-brand`, `text-brand`; вариант `dark:` по `html[data-color-scheme="dark"]`; тип `paths`, `components` в `src/shared/api/schema.d.ts`.

- [ ] **Step 1: Ветка и pnpm**

```bash
git switch docs/frontend-foundation-spec
git switch -c feat/frontend-foundation
corepack enable pnpm || npm i -g pnpm
pnpm -v
```
Expected: версия pnpm ≥ 9.

- [ ] **Step 2: Шаблон Vite**

Из корня репозитория:
```bash
pnpm create vite@latest frontend --template react-ts
```
Если спросит «Install with pnpm and start now?» — ответить **No**.
```bash
cd frontend
pnpm install
pnpm add @maxhub/max-ui framer-motion react-router @tanstack/react-query zustand openapi-fetch
pnpm add -D tailwindcss @tailwindcss/vite openapi-typescript vitest jsdom prettier eslint-config-prettier steiger @feature-sliced/steiger-plugin @types/node
rm -rf src/App.tsx src/App.css src/index.css src/main.tsx src/assets public/vite.svg
```

- [ ] **Step 3: Сверить Max UI**

```bash
ls node_modules/@maxhub/max-ui/dist
grep -oE "\b(MaxUI|Button|Typography|CellList|CellAction|CellInput|Panel|Flex)\b" node_modules/@maxhub/max-ui/dist/index.d.ts | sort -u
```
Expected: есть `styles.css`; все 8 имён найдены. Если путь к CSS другой — использовать фактический в Step 6.

- [ ] **Step 4: `vite.config.ts`**

Оставить импорт React-плагина таким, какой сгенерировал шаблон (`@vitejs/plugin-react` или `-swc`):

```ts
/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: { '/api': 'http://localhost:8000' },
  },
  test: {
    environment: 'jsdom',
  },
})
```

В `tsconfig.app.json` в `compilerOptions` добавить:
```json
"paths": { "@/*": ["./src/*"] }
```

- [ ] **Step 5: `index.html`**

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>Панель УК</title>
    <!-- Official Max bridge; no SRI: Max updates this script in place. -->
    <script src="https://st.max.ru/js/max-web-app.js"></script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/app/entrypoint/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Стили `src/app/styles/index.css`**

```css
@layer theme, base, maxui, components, utilities;

@import 'tailwindcss';
@import '@maxhub/max-ui/dist/styles.css' layer(maxui);

@custom-variant dark (&:where([data-color-scheme='dark'], [data-color-scheme='dark'] *));

:root {
  --brand: #2d7ff9;
}

@theme inline {
  --color-brand: var(--brand);
}

@layer base {
  body {
    @apply bg-neutral-50 text-neutral-900 antialiased dark:bg-neutral-950 dark:text-neutral-100;
  }
}
```

- [ ] **Step 7: Временная точка входа для проверки каскада**

`src/app/entrypoint/main.tsx`:
```tsx
import { Button, MaxUI } from '@maxhub/max-ui'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '../styles/index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MaxUI>
      <div className="p-4 text-brand">UK</div>
      <Button className="bg-red-500">Проверка каскада</Button>
    </MaxUI>
  </StrictMode>,
)
```

- [ ] **Step 8: Проверить каскад**

Run: `pnpm dev`, открыть `http://localhost:5173`.
Expected: текст «UK» синий (`--brand`), кнопка Max UI **красная** (утилита перебила стиль Max UI), у кнопки сохранились скругления и отступы Max UI (preflight не сломал компонент). В DevTools у `<button>` правило `bg-red-500` из `@layer utilities` активно.
Если `pnpm dev` падает на `layer(maxui)` или кнопка не красная — **остановиться и сообщить пользователю**, не обходить.

- [ ] **Step 9: Prettier, ESLint, Steiger, env**

`.prettierrc`:
```json
{ "semi": false, "singleQuote": true, "printWidth": 100 }
```

`.prettierignore`:
```
dist
pnpm-lock.yaml
src/shared/api/schema.d.ts
```

`eslint.config.js` — правка шаблона: в `globalIgnores([...])` добавить `'src/shared/api/schema.d.ts'`; импортировать `import eslintConfigPrettier from 'eslint-config-prettier/flat'` и добавить `eslintConfigPrettier` последним элементом массива конфигов.

`steiger.config.js`:
```js
import fsd from '@feature-sliced/steiger-plugin'
import { defineConfig } from 'steiger'

export default defineConfig([...fsd.configs.recommended])
```

`.env.template`:
```
# Dev login screen with seed users; backend must run with DEV_AUTH=true
VITE_DEV_AUTH=true
```
```bash
cp .env.template .env
```

- [ ] **Step 10: Скрипты и генерация типов API**

В `package.json` → `scripts` добавить (существующие `dev`, `build`, `preview`, `lint` оставить):
```json
"gen:api": "openapi-typescript ../backend/openapi.json -o src/shared/api/schema.d.ts",
"test": "vitest run",
"format": "prettier --write .",
"fsd": "steiger ./src",
"check": "bash scripts/check.sh"
```
```bash
pnpm gen:api
```
Expected: создан `src/shared/api/schema.d.ts`, в нём `export interface paths` с `"/api/v1/me"`.

- [ ] **Step 11: `scripts/check.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

pnpm exec tsc -b
pnpm exec eslint .
pnpm exec prettier --check .
pnpm exec steiger ./src
pnpm exec vitest run --passWithNoTests

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT
pnpm exec openapi-typescript ../backend/openapi.json -o "${tmp_dir}/schema.d.ts" > /dev/null
if ! diff -q --strip-trailing-cr "${tmp_dir}/schema.d.ts" src/shared/api/schema.d.ts > /dev/null; then
    echo "src/shared/api/schema.d.ts is outdated: run pnpm gen:api"
    exit 1
fi

pnpm build

echo "all checks passed"
```
```bash
chmod +x scripts/check.sh
pnpm format
bash scripts/check.sh
```
Expected: `all checks passed`; `dist/index.html` существует.

- [ ] **Step 12: Commit**

```bash
git add frontend
git commit -m "chore(web): scaffold frontend with vite, tailwind and max ui"
```

---

### Task 2: `shared/api` — клиент, ошибки, QueryClient

**Files:**
- Create: `frontend/src/shared/api/errors.ts`, `frontend/src/shared/api/client.ts`, `frontend/src/shared/api/query-client.ts`, `frontend/src/shared/api/index.ts`
- Test: `frontend/src/shared/api/errors.test.ts`, `frontend/src/shared/api/client.test.ts`, `frontend/src/shared/api/query-client.test.ts`

**Interfaces:**
- Consumes: `paths`, `components` из `./schema` (Task 1).
- Produces (из `@/shared/api`):
  - `api` — клиент `openapi-fetch` (`api.GET(path)`, `api.POST(path, { body })`);
  - `setTokenGetter(getter: () => string | null): void`, `setUnauthorizedHandler(handler: () => void): void`;
  - `class ApiError extends Error { status: number }`, `isApiError(error: unknown, status?: number): error is ApiError`;
  - `unwrap<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T>`;
  - `queryClient: QueryClient`;
  - `type components`, `type paths`.

- [ ] **Step 1: Тесты `errors.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import { ApiError, isApiError, unwrap } from './errors'

const response = (status: number) => new Response(null, { status })

describe('unwrap', () => {
  it('returns data for a successful response', async () => {
    const data = { id: 1 }
    await expect(unwrap(Promise.resolve({ data, response: response(200) }))).resolves.toBe(data)
  })

  it('returns undefined for 204', async () => {
    await expect(unwrap(Promise.resolve({ response: response(204) }))).resolves.toBeUndefined()
  })

  it('throws ApiError with backend detail message', async () => {
    const request = Promise.resolve({
      error: { detail: 'Пользователь не найден' },
      response: response(404),
    })
    await expect(unwrap(request)).rejects.toEqual(new ApiError(404, 'Пользователь не найден'))
  })

  it('falls back to a generic message when detail is not a string', async () => {
    const request = Promise.resolve({ error: { detail: [{ msg: 'x' }] }, response: response(422) })
    const error = await unwrap(request).catch((e: unknown) => e)
    expect(isApiError(error, 422)).toBe(true)
    expect((error as ApiError).message).toBe('Что-то пошло не так. Попробуйте ещё раз.')
  })
})

describe('isApiError', () => {
  it('matches status when given', () => {
    const error = new ApiError(403, 'no')
    expect(isApiError(error)).toBe(true)
    expect(isApiError(error, 403)).toBe(true)
    expect(isApiError(error, 401)).toBe(false)
    expect(isApiError(new Error('x'))).toBe(false)
  })
})
```

- [ ] **Step 2: Запустить — должно упасть**

Run: `pnpm exec vitest run src/shared/api/errors.test.ts`
Expected: FAIL — `Failed to resolve import "./errors"`.

- [ ] **Step 3: `errors.ts`**

```ts
const FALLBACK_MESSAGE = 'Что-то пошло не так. Попробуйте ещё раз.'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function isApiError(error: unknown, status?: number): error is ApiError {
  return error instanceof ApiError && (status === undefined || error.status === status)
}

function messageFrom(body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
    return body.detail
  }
  return FALLBACK_MESSAGE
}

interface FetchResult<T> {
  data?: T
  error?: unknown
  response: Response
}

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await request
  if (!response.ok) {
    throw new ApiError(response.status, messageFrom(error))
  }
  return data as T
}
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/shared/api/errors.test.ts`
Expected: PASS (5 тестов).

- [ ] **Step 5: Тесты `client.test.ts`**

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { authMiddleware, setTokenGetter, setUnauthorizedHandler } from './client'

type OnRequestParams = Parameters<NonNullable<typeof authMiddleware.onRequest>>[0]
type OnResponseParams = Parameters<NonNullable<typeof authMiddleware.onResponse>>[0]

const URL_ME = 'http://localhost/api/v1/me'

async function runOnRequest(request: Request): Promise<Request> {
  return (await authMiddleware.onRequest!({ request } as OnRequestParams)) as Request
}

async function runOnResponse(request: Request, status: number): Promise<void> {
  await authMiddleware.onResponse!({
    request,
    response: new Response(null, { status }),
  } as OnResponseParams)
}

afterEach(() => {
  setTokenGetter(() => null)
  setUnauthorizedHandler(() => {})
})

describe('authMiddleware', () => {
  it('adds a bearer token when there is one', async () => {
    setTokenGetter(() => 'abc')
    const request = await runOnRequest(new Request(URL_ME))
    expect(request.headers.get('Authorization')).toBe('Bearer abc')
  })

  it('sends no Authorization header without a token', async () => {
    const request = await runOnRequest(new Request(URL_ME))
    expect(request.headers.has('Authorization')).toBe(false)
  })

  it('calls the unauthorized handler on 401 for an authenticated request', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    const request = new Request(URL_ME, { headers: { Authorization: 'Bearer stale' } })
    await runOnResponse(request, 401)
    expect(handler).toHaveBeenCalledOnce()
  })

  it('ignores 401 for a request sent without a token', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    await runOnResponse(new Request('http://localhost/api/v1/auth/max'), 401)
    expect(handler).not.toHaveBeenCalled()
  })

  it('ignores 403', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    const request = new Request(URL_ME, { headers: { Authorization: 'Bearer t' } })
    await runOnResponse(request, 403)
    expect(handler).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 6: Запустить — должно упасть**

Run: `pnpm exec vitest run src/shared/api/client.test.ts`
Expected: FAIL — `Failed to resolve import "./client"`.

- [ ] **Step 7: `client.ts`**

```ts
import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './schema'

let getToken: () => string | null = () => null
let handleUnauthorized: () => void = () => {}

export function setTokenGetter(getter: () => string | null): void {
  getToken = getter
}

export function setUnauthorizedHandler(handler: () => void): void {
  handleUnauthorized = handler
}

export const authMiddleware: Middleware = {
  onRequest({ request }) {
    const token = getToken()
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`)
    }
    return request
  },
  onResponse({ request, response }) {
    // Only a rejected token means the session is gone; login endpoints send no token.
    if (response.status === 401 && request.headers.has('Authorization')) {
      handleUnauthorized()
    }
    return response
  },
}

export const api = createClient<paths>({ baseUrl: window.location.origin })
api.use(authMiddleware)
```

- [ ] **Step 8: Запустить — проходит**

Run: `pnpm exec vitest run src/shared/api/client.test.ts`
Expected: PASS (5 тестов).

- [ ] **Step 9: Тесты `query-client.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import { ApiError } from './errors'
import { shouldRetry } from './query-client'

describe('shouldRetry', () => {
  it.each([401, 403, 404, 422])('does not retry %i', (status) => {
    expect(shouldRetry(0, new ApiError(status, 'x'))).toBe(false)
  })

  it('retries server errors and network failures twice', () => {
    expect(shouldRetry(0, new ApiError(500, 'x'))).toBe(true)
    expect(shouldRetry(1, new TypeError('Failed to fetch'))).toBe(true)
    expect(shouldRetry(2, new TypeError('Failed to fetch'))).toBe(false)
  })
})
```

- [ ] **Step 10: Запустить — должно упасть**

Run: `pnpm exec vitest run src/shared/api/query-client.test.ts`
Expected: FAIL — `Failed to resolve import "./query-client"`.

- [ ] **Step 11: `query-client.ts` и `index.ts`**

`query-client.ts`:
```ts
import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './errors'

export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status < 500) {
    return false
  }
  return failureCount < 2
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: shouldRetry, staleTime: 30_000 },
    mutations: { retry: false },
  },
})
```

`index.ts`:
```ts
export { api, setTokenGetter, setUnauthorizedHandler } from './client'
export { ApiError, isApiError, unwrap } from './errors'
export { queryClient } from './query-client'
export type { components, paths } from './schema'
```

- [ ] **Step 12: Запустить все тесты и проверку типов**

Run: `pnpm exec vitest run src/shared/api && pnpm exec tsc -b`
Expected: PASS (15 тестов), `tsc` без ошибок. Вывод типа `T` в `unwrap(api.GET(...))` впервые проверяется в Task 4 (`useMe().data`); если там `data` окажется `unknown`/`never` — остановиться и сообщить фактическую ошибку `tsc`.

- [ ] **Step 13: Commit**

```bash
git add frontend/src/shared/api
git commit -m "feat(web): add typed api client with auth middleware"
```

---

### Task 3: `shared/config`, `shared/lib/max-bridge`, `shared/lib/color-scheme`

**Files:**
- Create: `frontend/src/shared/config/{env.ts, routes.ts, index.ts}`, `frontend/src/shared/lib/max-bridge/{types.ts, bridge.ts, index.ts}`, `frontend/src/shared/lib/color-scheme/{use-color-scheme.ts, index.ts}`
- Test: `frontend/src/shared/lib/max-bridge/bridge.test.ts`

**Interfaces:**
- Produces:
  - `@/shared/config`: `isDevAuthEnabled: boolean`; `routePaths = { home: '/', login: '/login', staff: '/staff', client: '/client' }`;
  - `@/shared/lib/max-bridge`: `isInMax(): boolean`, `getInitData(): string`, `getStartParam(): string | null`;
  - `@/shared/lib/color-scheme`: `type ColorScheme = 'light' | 'dark'`, `useColorScheme(): ColorScheme`.

- [ ] **Step 1: `shared/config`**

`env.ts`:
```ts
export const isDevAuthEnabled = import.meta.env.VITE_DEV_AUTH === 'true'
```

`routes.ts`:
```ts
export const routePaths = {
  home: '/',
  login: '/login',
  staff: '/staff',
  client: '/client',
} as const
```

`index.ts`:
```ts
export { isDevAuthEnabled } from './env'
export { routePaths } from './routes'
```

- [ ] **Step 2: Тесты `bridge.test.ts`**

```ts
import { afterEach, describe, expect, it } from 'vitest'
import { getInitData, getStartParam, isInMax } from './bridge'

afterEach(() => {
  delete window.WebApp
})

describe('max bridge', () => {
  it('is a plain browser when the Max script is absent', () => {
    expect(isInMax()).toBe(false)
    expect(getInitData()).toBe('')
    expect(getStartParam()).toBeNull()
  })

  it('is a plain browser when initData is empty (script loaded outside Max)', () => {
    window.WebApp = { initData: '' }
    expect(isInMax()).toBe(false)
  })

  it('reads initData and start_param inside Max', () => {
    window.WebApp = { initData: 'user=1&hash=x', initDataUnsafe: { start_param: 'ticket_1042' } }
    expect(isInMax()).toBe(true)
    expect(getInitData()).toBe('user=1&hash=x')
    expect(getStartParam()).toBe('ticket_1042')
  })

  it('ignores a non-string or empty start_param', () => {
    window.WebApp = { initData: 'x', initDataUnsafe: { start_param: { value: 1 } } }
    expect(getStartParam()).toBeNull()
    window.WebApp = { initData: 'x', initDataUnsafe: { start_param: '' } }
    expect(getStartParam()).toBeNull()
  })
})
```

- [ ] **Step 3: Запустить — должно упасть**

Run: `pnpm exec vitest run src/shared/lib/max-bridge`
Expected: FAIL — `Failed to resolve import "./bridge"`.

- [ ] **Step 4: Реализация `max-bridge`**

`types.ts`:
```ts
// Only the fields we use from https://st.max.ru/js/max-web-app.js.
export interface MaxWebApp {
  initData: string
  // The start_param format is confirmed live in Ф2, so keep it unknown here.
  initDataUnsafe?: { start_param?: unknown }
}

declare global {
  interface Window {
    WebApp?: MaxWebApp
  }
}
```

`bridge.ts`:
```ts
import type {} from './types'

export function isInMax(): boolean {
  return Boolean(window.WebApp?.initData)
}

export function getInitData(): string {
  return window.WebApp?.initData ?? ''
}

export function getStartParam(): string | null {
  const value = window.WebApp?.initDataUnsafe?.start_param
  return typeof value === 'string' && value !== '' ? value : null
}
```

`index.ts`:
```ts
export { getInitData, getStartParam, isInMax } from './bridge'
```

- [ ] **Step 5: Запустить — проходит**

Run: `pnpm exec vitest run src/shared/lib/max-bridge`
Expected: PASS (4 теста).

- [ ] **Step 6: `color-scheme`**

`use-color-scheme.ts`:
```ts
import { useSyncExternalStore } from 'react'

export type ColorScheme = 'light' | 'dark'

const DARK_QUERY = '(prefers-color-scheme: dark)'

function subscribe(onChange: () => void): () => void {
  const media = window.matchMedia(DARK_QUERY)
  media.addEventListener('change', onChange)
  return () => media.removeEventListener('change', onChange)
}

function getSnapshot(): ColorScheme {
  return window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light'
}

export function useColorScheme(): ColorScheme {
  return useSyncExternalStore(subscribe, getSnapshot)
}
```

`index.ts`:
```ts
export { useColorScheme, type ColorScheme } from './use-color-scheme'
```

- [ ] **Step 7: Проверка**

Run: `pnpm exec tsc -b && pnpm exec steiger ./src`
Expected: без ошибок.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/shared/config frontend/src/shared/lib
git commit -m "feat(web): add max bridge, color scheme and route config"
```

---

### Task 4: `entities/user`, `entities/session`

**Files:**
- Create: `frontend/src/entities/user/{model/user.ts, index.ts}`, `frontend/src/entities/session/{model/session-store.ts, model/use-start-session.ts, api/me.ts, index.ts}`
- Test: `frontend/src/entities/user/model/user.test.ts`, `frontend/src/entities/session/model/session-store.test.ts`

**Interfaces:**
- Consumes: `components`, `api`, `unwrap` из `@/shared/api`.
- Produces:
  - `@/entities/user`: `type User`, `type UserRole`, `isStaff(user)`, `isAdmin(user)`, `isClient(user)`, `getDisplayName(user): string`, `roleLabels: Record<UserRole, string>`;
  - `@/entities/session`: `useSessionStore` (Zustand: `token: string | null`, `setToken(token: string)`, `clear()`), `meQueryKey = ['me']`, `useMe()` (`UseQueryResult<User>`), `useStartSession(): (token: string, user: User) => void`.

- [ ] **Step 1: Тесты `user.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import { getDisplayName, isAdmin, isClient, isStaff, type User } from './user'

const user = (overrides: Partial<User> = {}): User => ({
  id: 1,
  max_user_id: 1000001,
  first_name: 'Анна',
  last_name: null,
  username: null,
  phone: null,
  role: 'CLIENT',
  ...overrides,
})

describe('roles', () => {
  it('treats managers and admins as staff', () => {
    expect(isStaff(user({ role: 'MANAGER' }))).toBe(true)
    expect(isStaff(user({ role: 'ADMIN' }))).toBe(true)
    expect(isStaff(user({ role: 'CLIENT' }))).toBe(false)
  })

  it('recognises admins and clients', () => {
    expect(isAdmin(user({ role: 'ADMIN' }))).toBe(true)
    expect(isAdmin(user({ role: 'MANAGER' }))).toBe(false)
    expect(isClient(user({ role: 'CLIENT' }))).toBe(true)
    expect(isClient(user({ role: 'MANAGER' }))).toBe(false)
  })
})

describe('getDisplayName', () => {
  it('joins first and last name', () => {
    expect(getDisplayName(user({ last_name: 'Петрова' }))).toBe('Анна Петрова')
  })

  it('uses the first name alone when there is no last name', () => {
    expect(getDisplayName(user())).toBe('Анна')
  })
})
```

- [ ] **Step 2: Запустить — должно упасть**

Run: `pnpm exec vitest run src/entities/user`
Expected: FAIL — `Failed to resolve import "./user"`.

- [ ] **Step 3: `entities/user`**

`model/user.ts`:
```ts
import type { components } from '@/shared/api'

export type User = components['schemas']['UserResponse']
export type UserRole = User['role']

export const roleLabels: Record<UserRole, string> = {
  CLIENT: 'Клиент',
  MANAGER: 'Менеджер',
  ADMIN: 'Администратор',
}

export function isStaff(user: User): boolean {
  return user.role === 'MANAGER' || user.role === 'ADMIN'
}

export function isAdmin(user: User): boolean {
  return user.role === 'ADMIN'
}

export function isClient(user: User): boolean {
  return user.role === 'CLIENT'
}

export function getDisplayName(user: User): string {
  return [user.first_name, user.last_name].filter(Boolean).join(' ')
}
```

`index.ts`:
```ts
export {
  getDisplayName,
  isAdmin,
  isClient,
  isStaff,
  roleLabels,
  type User,
  type UserRole,
} from './model/user'
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/entities/user`
Expected: PASS (4 теста).

- [ ] **Step 5: Тесты `session-store.test.ts`**

```ts
import { beforeEach, describe, expect, it } from 'vitest'
import { useSessionStore } from './session-store'

beforeEach(() => {
  useSessionStore.getState().clear()
  localStorage.clear()
})

describe('session store', () => {
  it('stores the token and persists it', () => {
    useSessionStore.getState().setToken('abc')
    expect(useSessionStore.getState().token).toBe('abc')
    expect(JSON.parse(localStorage.getItem('uk-session')!).state).toEqual({ token: 'abc' })
  })

  it('clears the token', () => {
    useSessionStore.getState().setToken('abc')
    useSessionStore.getState().clear()
    expect(useSessionStore.getState().token).toBeNull()
  })
})
```

- [ ] **Step 6: Запустить — должно упасть**

Run: `pnpm exec vitest run src/entities/session`
Expected: FAIL — `Failed to resolve import "./session-store"`.

- [ ] **Step 7: `entities/session`**

`model/session-store.ts`:
```ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SessionState {
  token: string | null
  setToken: (token: string) => void
  clear: () => void
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      token: null,
      setToken: (token) => set({ token }),
      clear: () => set({ token: null }),
    }),
    { name: 'uk-session', partialize: (state) => ({ token: state.token }) },
  ),
)
```

`api/me.ts`:
```ts
import { useQuery } from '@tanstack/react-query'
import { api, unwrap } from '@/shared/api'
import { useSessionStore } from '../model/session-store'

export const meQueryKey = ['me'] as const

export function fetchMe() {
  return unwrap(api.GET('/api/v1/me'))
}

export function useMe() {
  const token = useSessionStore((state) => state.token)
  return useQuery({ queryKey: meQueryKey, queryFn: fetchMe, enabled: token !== null })
}
```

`model/use-start-session.ts`:
```ts
import { useQueryClient } from '@tanstack/react-query'
import type { components } from '@/shared/api'
import { meQueryKey } from '../api/me'
import { useSessionStore } from './session-store'

type User = components['schemas']['UserResponse']

export function useStartSession(): (token: string, user: User) => void {
  const queryClient = useQueryClient()
  const setToken = useSessionStore((state) => state.setToken)
  return (token, user) => {
    // User first: once the token appears, the session gate already has /me data.
    queryClient.setQueryData(meQueryKey, user)
    setToken(token)
  }
}
```

`index.ts`:
```ts
export { meQueryKey, useMe } from './api/me'
export { useSessionStore } from './model/session-store'
export { useStartSession } from './model/use-start-session'
```

- [ ] **Step 8: Запустить тесты, типы, FSD**

Run: `pnpm exec vitest run src/entities && pnpm exec tsc -b && pnpm exec steiger ./src`
Expected: PASS (6 тестов); `tsc` без ошибок (в т.ч. `useMe().data` имеет тип `UserResponse`); Steiger без ошибок. Если Steiger сообщает `fsd/insignificant-slice` — см. Global Constraints: остановиться и спросить.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/entities
git commit -m "feat(web): add user and session entities"
```

---

### Task 5: Фичи `auth-by-max`, `auth-dev`, `logout`

**Files:**
- Create: `frontend/src/features/auth-by-max/{api/login-by-max.ts, model/use-login-by-max.ts, index.ts}`, `frontend/src/features/auth-dev/{api/dev-login.ts, config/seed-users.ts, lib/parse-max-user-id.ts, model/use-dev-login.ts, ui/DevLoginForm.tsx, index.ts}`, `frontend/src/features/logout/{api/logout.ts, model/use-logout.ts, ui/LogoutButton.tsx, index.ts}`
- Test: `frontend/src/features/auth-dev/lib/parse-max-user-id.test.ts`

**Interfaces:**
- Consumes: `api`, `unwrap` (`@/shared/api`); `routePaths` (`@/shared/config`); `getInitData`, `isInMax` (`@/shared/lib/max-bridge`); `useStartSession`, `useSessionStore` (`@/entities/session`).
- Produces:
  - `@/features/auth-by-max`: `useLoginByMax()` — `UseMutationResult` без аргументов (`mutate()`), при успехе стартует сессию;
  - `@/features/auth-dev`: `DevLoginForm` (компонент без пропсов, после входа — `navigate('/')`);
  - `@/features/logout`: `LogoutButton` (компонент без пропсов; в Max не рендерится).

- [ ] **Step 1: Тесты `parse-max-user-id.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import { parseMaxUserId } from './parse-max-user-id'

describe('parseMaxUserId', () => {
  it('parses a positive integer, trimming spaces', () => {
    expect(parseMaxUserId(' 1000002 ')).toBe(1000002)
  })

  it.each(['', '   ', 'abc', '12a', '-5', '0', '1.5', '99999999999999999999'])(
    'rejects %j',
    (input) => {
      expect(parseMaxUserId(input)).toBeNull()
    },
  )
})
```

- [ ] **Step 2: Запустить — должно упасть**

Run: `pnpm exec vitest run src/features/auth-dev`
Expected: FAIL — `Failed to resolve import "./parse-max-user-id"`.

- [ ] **Step 3: `lib/parse-max-user-id.ts`**

```ts
export function parseMaxUserId(input: string): number | null {
  const value = input.trim()
  if (!/^\d+$/.test(value)) {
    return null
  }
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/features/auth-dev`
Expected: PASS (9 тестов).

- [ ] **Step 5: `auth-by-max`**

`api/login-by-max.ts`:
```ts
import { api, unwrap } from '@/shared/api'

export function loginByMax(initData: string) {
  return unwrap(api.POST('/api/v1/auth/max', { body: { init_data: initData } }))
}
```

`model/use-login-by-max.ts`:
```ts
import { useMutation } from '@tanstack/react-query'
import { useStartSession } from '@/entities/session'
import { getInitData } from '@/shared/lib/max-bridge'
import { loginByMax } from '../api/login-by-max'

export function useLoginByMax() {
  const startSession = useStartSession()
  return useMutation({
    mutationFn: () => loginByMax(getInitData()),
    onSuccess: ({ token, user }) => startSession(token, user),
  })
}
```

`index.ts`:
```ts
export { useLoginByMax } from './model/use-login-by-max'
```

- [ ] **Step 6: `auth-dev`**

`config/seed-users.ts`:
```ts
// Users from backend/scripts/seed.py.
export const seedUsers = [
  { maxUserId: 1000001, label: 'Анна — администратор' },
  { maxUserId: 1000002, label: 'Игорь — менеджер' },
  { maxUserId: 1000003, label: 'Мария — клиент' },
] as const
```

`api/dev-login.ts`:
```ts
import { api, unwrap } from '@/shared/api'

export function devLogin(maxUserId: number) {
  return unwrap(api.POST('/api/v1/auth/dev', { body: { max_user_id: maxUserId } }))
}
```

`model/use-dev-login.ts`:
```ts
import { useMutation } from '@tanstack/react-query'
import { useStartSession } from '@/entities/session'
import { devLogin } from '../api/dev-login'

export function useDevLogin() {
  const startSession = useStartSession()
  return useMutation({
    mutationFn: devLogin,
    onSuccess: ({ token, user }) => startSession(token, user),
  })
}
```

`ui/DevLoginForm.tsx`:
```tsx
import { Button, CellAction, CellInput, CellList } from '@maxhub/max-ui'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { routePaths } from '@/shared/config'
import { seedUsers } from '../config/seed-users'
import { parseMaxUserId } from '../lib/parse-max-user-id'
import { useDevLogin } from '../model/use-dev-login'

export function DevLoginForm() {
  const navigate = useNavigate()
  const login = useDevLogin()
  const [customId, setCustomId] = useState('')
  const parsedId = parseMaxUserId(customId)

  const submit = (maxUserId: number) => {
    login.mutate(maxUserId, { onSuccess: () => navigate(routePaths.home, { replace: true }) })
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (parsedId !== null) {
      submit(parsedId)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <CellList mode="island" header="Демо-пользователи">
        {seedUsers.map((user) => (
          <CellAction
            key={user.maxUserId}
            showChevron
            disabled={login.isPending}
            onClick={() => submit(user.maxUserId)}
          >
            {user.label}
          </CellAction>
        ))}
      </CellList>

      <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
        <CellList mode="island" header="Другой пользователь">
          <CellInput
            placeholder="max_user_id"
            inputMode="numeric"
            value={customId}
            onChange={(event) => setCustomId(event.target.value)}
          />
        </CellList>
        <Button
          type="submit"
          size="large"
          stretched
          disabled={parsedId === null}
          loading={login.isPending}
        >
          Войти
        </Button>
      </form>

      {login.error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {login.error.message}
        </p>
      )}
    </div>
  )
}
```

`index.ts`:
```ts
export { DevLoginForm } from './ui/DevLoginForm'
```

- [ ] **Step 7: `logout`**

`api/logout.ts`:
```ts
import { api, unwrap } from '@/shared/api'

export function logout() {
  return unwrap(api.POST('/api/v1/auth/logout'))
}
```

`model/use-logout.ts`:
```ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { useSessionStore } from '@/entities/session'
import { routePaths } from '@/shared/config'
import { logout } from '../api/logout'

export function useLogout() {
  const queryClient = useQueryClient()
  const clear = useSessionStore((state) => state.clear)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: logout,
    // Leave locally even if the server call fails: the user asked to sign out.
    onSettled: () => {
      clear()
      queryClient.clear()
      navigate(routePaths.login, { replace: true })
    },
  })
}
```

`ui/LogoutButton.tsx`:
```tsx
import { Button } from '@maxhub/max-ui'
import { isInMax } from '@/shared/lib/max-bridge'
import { useLogout } from '../model/use-logout'

export function LogoutButton() {
  const logout = useLogout()
  if (isInMax()) {
    return null
  }
  return (
    <Button
      mode="tertiary"
      appearance="neutral"
      size="small"
      loading={logout.isPending}
      onClick={() => logout.mutate()}
    >
      Выйти
    </Button>
  )
}
```

`index.ts`:
```ts
export { LogoutButton } from './ui/LogoutButton'
```

- [ ] **Step 8: Проверка**

Run: `pnpm exec tsc -b && pnpm exec eslint src/features && pnpm exec steiger ./src`
Expected: без ошибок. Если `CellInput` не принимает `value`/`onChange`/`inputMode` — посмотреть его пропсы в `node_modules/@maxhub/max-ui/dist` и сообщить; не подменять на нативный `<input>` молча. Если Steiger сообщает `fsd/insignificant-slice` — остановиться и спросить (Global Constraints).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/features
git commit -m "feat(web): add max, dev login and logout features"
```

---

### Task 6: Общий UI, каркас `app-shell`, страницы

**Files:**
- Create: `frontend/src/shared/ui/page-transition/{PageTransition.tsx, index.ts}`, `frontend/src/shared/ui/splash-screen/{SplashScreen.tsx, index.ts}`, `frontend/src/shared/ui/status-screen/{StatusScreen.tsx, index.ts}`, `frontend/src/widgets/app-shell/{model/nav.ts, ui/AppShell.tsx, index.ts}`, `frontend/src/pages/{login,staff-home,client-home,not-found}/{ui/*Page.tsx, index.ts}`
- Test: `frontend/src/widgets/app-shell/model/nav.test.ts`

**Interfaces:**
- Consumes: `useMe`, `useSessionStore` (`@/entities/session`); `isAdmin`, `getDisplayName`, `roleLabels`, `User` (`@/entities/user`); `LogoutButton` (`@/features/logout`); `DevLoginForm` (`@/features/auth-dev`); `routePaths`, `isDevAuthEnabled` (`@/shared/config`); `isInMax` (`@/shared/lib/max-bridge`).
- Produces:
  - `@/shared/ui/page-transition`: `PageTransition({ children, className? })`;
  - `@/shared/ui/splash-screen`: `SplashScreen()`;
  - `@/shared/ui/status-screen`: `StatusScreen({ title: string, text: string, action?: ReactNode })`;
  - `@/widgets/app-shell`: `AppShell` (layout-компонент с `<Outlet />`);
  - `@/pages/login`: `LoginPage`; `@/pages/staff-home`: `StaffHomePage`; `@/pages/client-home`: `ClientHomePage`; `@/pages/not-found`: `NotFoundPage`.

- [ ] **Step 1: Тесты `nav.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import type { User } from '@/entities/user'
import { visibleNavItems } from './nav'

const user = (role: User['role']): User => ({
  id: 1,
  max_user_id: 1,
  first_name: 'Тест',
  last_name: null,
  username: null,
  phone: null,
  role,
})

describe('visibleNavItems', () => {
  it('shows only tickets to a manager', () => {
    expect(visibleNavItems(user('MANAGER')).map((item) => item.key)).toEqual(['tickets'])
  })

  it('shows admin sections to an admin', () => {
    expect(visibleNavItems(user('ADMIN')).map((item) => item.key)).toEqual([
      'tickets',
      'content',
      'users',
    ])
  })
})
```

- [ ] **Step 2: Запустить — должно упасть**

Run: `pnpm exec vitest run src/widgets`
Expected: FAIL — `Failed to resolve import "./nav"`.

- [ ] **Step 3: `widgets/app-shell/model/nav.ts`**

```ts
import { isAdmin, type User } from '@/entities/user'
import { routePaths } from '@/shared/config'

export interface NavItem {
  key: string
  label: string
  // null — the section is not built yet (Ф5): shown, but inactive.
  to: string | null
  adminOnly: boolean
}

const navItems: NavItem[] = [
  { key: 'tickets', label: 'Обращения', to: routePaths.staff, adminOnly: false },
  { key: 'content', label: 'Контент', to: null, adminOnly: true },
  { key: 'users', label: 'Пользователи', to: null, adminOnly: true },
]

export function visibleNavItems(user: User): NavItem[] {
  return navItems.filter((item) => !item.adminOnly || isAdmin(user))
}
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/widgets`
Expected: PASS (2 теста).

- [ ] **Step 5: `shared/ui`**

`page-transition/PageTransition.tsx`:
```tsx
import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

interface PageTransitionProps {
  children: ReactNode
  className?: string
}

export function PageTransition({ children, className }: PageTransitionProps) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}
```
`page-transition/index.ts`:
```ts
export { PageTransition } from './PageTransition'
```

`splash-screen/SplashScreen.tsx`:
```tsx
import { motion } from 'framer-motion'

export function SplashScreen() {
  return (
    <div className="flex min-h-dvh items-center justify-center" aria-busy="true">
      <motion.div
        className="size-10 rounded-full border-4 border-brand/20 border-t-brand"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, rotate: 360 }}
        transition={{
          opacity: { duration: 0.3, delay: 0.2 },
          rotate: { duration: 0.9, ease: 'linear', repeat: Infinity },
        }}
        aria-label="Загрузка"
      />
    </div>
  )
}
```
`splash-screen/index.ts`:
```ts
export { SplashScreen } from './SplashScreen'
```

`status-screen/StatusScreen.tsx`:
```tsx
import { Typography } from '@maxhub/max-ui'
import type { ReactNode } from 'react'
import { PageTransition } from '../page-transition'

interface StatusScreenProps {
  title: string
  text: string
  action?: ReactNode
}

export function StatusScreen({ title, text, action }: StatusScreenProps) {
  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <PageTransition className="flex max-w-sm flex-col items-center gap-3 text-center">
        <Typography.Title>{title}</Typography.Title>
        <p className="text-neutral-500 dark:text-neutral-400">{text}</p>
        {action && <div className="mt-2">{action}</div>}
      </PageTransition>
    </div>
  )
}
```
`status-screen/index.ts`:
```ts
export { StatusScreen } from './StatusScreen'
```

- [ ] **Step 6: `widgets/app-shell/ui/AppShell.tsx` и `index.ts`**

```tsx
import { NavLink, Outlet } from 'react-router'
import { useMe } from '@/entities/session'
import { getDisplayName, roleLabels } from '@/entities/user'
import { LogoutButton } from '@/features/logout'
import { visibleNavItems, type NavItem } from '../model/nav'

const DISABLED_HINT = 'Раздел появится позже'

function SideLink({ item }: { item: NavItem }) {
  if (item.to === null) {
    return (
      <span className="rounded-lg px-3 py-2 text-neutral-400" aria-disabled="true" title={DISABLED_HINT}>
        {item.label}
      </span>
    )
  }
  return (
    <NavLink
      to={item.to}
      end
      className={({ isActive }) =>
        `rounded-lg px-3 py-2 transition-colors ${
          isActive
            ? 'bg-brand/10 font-medium text-brand'
            : 'hover:bg-neutral-100 dark:hover:bg-neutral-900'
        }`
      }
    >
      {item.label}
    </NavLink>
  )
}

function TabLink({ item }: { item: NavItem }) {
  const base = 'flex flex-1 items-center justify-center py-3 text-xs'
  if (item.to === null) {
    return (
      <span className={`${base} text-neutral-400`} aria-disabled="true" title={DISABLED_HINT}>
        {item.label}
      </span>
    )
  }
  return (
    <NavLink
      to={item.to}
      end
      className={({ isActive }) => `${base} ${isActive ? 'font-medium text-brand' : ''}`}
    >
      {item.label}
    </NavLink>
  )
}

export function AppShell() {
  const { data: user } = useMe()
  if (!user) {
    return null
  }
  const items = visibleNavItems(user)
  const name = getDisplayName(user)

  return (
    <div className="flex min-h-dvh">
      <aside className="hidden w-64 shrink-0 flex-col gap-6 border-r border-neutral-200 p-4 lg:flex dark:border-neutral-800">
        <div className="px-3 text-lg font-semibold">Панель УК</div>
        <nav className="flex flex-col gap-1">
          {items.map((item) => (
            <SideLink key={item.key} item={item} />
          ))}
        </nav>
        <div className="mt-auto flex flex-col items-start gap-2 px-3 text-sm">
          <div>
            <div className="font-medium">{name}</div>
            <div className="text-neutral-500">{roleLabels[user.role]}</div>
          </div>
          <LogoutButton />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-neutral-200 px-4 py-2 lg:hidden dark:border-neutral-800">
          <span className="text-sm font-medium">{name}</span>
          <LogoutButton />
        </header>
        <main className="flex-1 pb-[calc(3rem+env(safe-area-inset-bottom))] lg:pb-0">
          <Outlet />
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 flex border-t border-neutral-200 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden dark:border-neutral-800 dark:bg-neutral-900">
        {items.map((item) => (
          <TabLink key={item.key} item={item} />
        ))}
      </nav>
    </div>
  )
}
```

`index.ts`:
```ts
export { AppShell } from './ui/AppShell'
```

- [ ] **Step 7: Страницы**

`pages/staff-home/ui/StaffHomePage.tsx`:
```tsx
import { Typography } from '@maxhub/max-ui'
import { PageTransition } from '@/shared/ui/page-transition'

export function StaffHomePage() {
  return (
    <PageTransition className="p-4 lg:p-8">
      <Typography.Title>Обращения</Typography.Title>
      <p className="mt-2 text-neutral-500 dark:text-neutral-400">
        Здесь появится список обращений жильцов.
      </p>
    </PageTransition>
  )
}
```
`pages/staff-home/index.ts`:
```ts
export { StaffHomePage } from './ui/StaffHomePage'
```

`pages/client-home/ui/ClientHomePage.tsx`:
```tsx
import { StatusScreen } from '@/shared/ui/status-screen'

export function ClientHomePage() {
  return (
    <StatusScreen
      title="Заявки подаются в чате с ботом"
      text="Напишите боту, чтобы подать заявку или узнать её статус."
    />
  )
}
```
`pages/client-home/index.ts`:
```ts
export { ClientHomePage } from './ui/ClientHomePage'
```

`pages/not-found/ui/NotFoundPage.tsx`:
```tsx
import { Button } from '@maxhub/max-ui'
import { Link } from 'react-router'
import { routePaths } from '@/shared/config'
import { StatusScreen } from '@/shared/ui/status-screen'

export function NotFoundPage() {
  return (
    <StatusScreen
      title="Страница не найдена"
      text="Возможно, ссылка устарела."
      action={
        <Button asChild mode="secondary">
          <Link to={routePaths.home}>На главную</Link>
        </Button>
      }
    />
  )
}
```
`pages/not-found/index.ts`:
```ts
export { NotFoundPage } from './ui/NotFoundPage'
```

`pages/login/ui/LoginPage.tsx`:
```tsx
import { Typography } from '@maxhub/max-ui'
import { Navigate } from 'react-router'
import { useSessionStore } from '@/entities/session'
import { DevLoginForm } from '@/features/auth-dev'
import { isDevAuthEnabled, routePaths } from '@/shared/config'
import { isInMax } from '@/shared/lib/max-bridge'
import { PageTransition } from '@/shared/ui/page-transition'

export function LoginPage() {
  const token = useSessionStore((state) => state.token)
  // Inside Max sign-in is automatic; a signed-in user has nothing to do here.
  if (isInMax() || token !== null) {
    return <Navigate to={routePaths.home} replace />
  }

  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <PageTransition className="flex w-full max-w-sm flex-col gap-6">
        <Typography.Title>Вход в панель УК</Typography.Title>
        {isDevAuthEnabled ? (
          <DevLoginForm />
        ) : (
          <p className="text-neutral-500 dark:text-neutral-400">
            Напишите боту команду /panel — он пришлёт ссылку для входа.
          </p>
        )}
      </PageTransition>
    </div>
  )
}
```
`pages/login/index.ts`:
```ts
export { LoginPage } from './ui/LoginPage'
```

- [ ] **Step 8: Проверка**

Run: `pnpm exec vitest run && pnpm exec tsc -b && pnpm exec eslint . && pnpm exec steiger ./src`
Expected: все тесты PASS, остальное без ошибок (warnings `react-refresh` допустимы). `fsd/insignificant-slice` — остановиться и спросить.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/shared/ui frontend/src/widgets frontend/src/pages
git commit -m "feat(web): add app shell and placeholder pages"
```

---

### Task 7: `app` — провайдеры, тема, роутер, вход

**Files:**
- Create: `frontend/src/app/routes/{session-state.ts, home-path.ts, SessionGate.tsx, RequireRole.tsx, RoleRedirect.tsx, router.tsx}`, `frontend/src/app/providers/{api-session.ts, ThemeProvider.tsx, AppProviders.tsx}`
- Modify: `frontend/src/app/entrypoint/main.tsx` (заменить временный код из Task 1)
- Test: `frontend/src/app/routes/session-state.test.ts`, `frontend/src/app/routes/home-path.test.ts`

**Interfaces:**
- Consumes: всё из Tasks 2–6.
- Produces: `resolveSessionState(input: SessionInput): SessionState`; `homePathFor(user: User): string`; `router`; `AppProviders`.

- [ ] **Step 1: Тесты `session-state.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import type { User } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { resolveSessionState, type SessionInput } from './session-state'

const user: User = {
  id: 1,
  max_user_id: 1000002,
  first_name: 'Игорь',
  last_name: null,
  username: null,
  phone: null,
  role: 'MANAGER',
}

const input = (overrides: Partial<SessionInput> = {}): SessionInput => ({
  token: null,
  inMax: false,
  me: { data: undefined, error: null },
  maxLogin: { error: null },
  ...overrides,
})

describe('resolveSessionState with a token', () => {
  it('is ready when /me returned the user', () => {
    expect(resolveSessionState(input({ token: 't', me: { data: user, error: null } }))).toEqual({
      kind: 'ready',
      user,
    })
  })

  it('is loading while /me is in flight', () => {
    expect(resolveSessionState(input({ token: 't' }))).toEqual({ kind: 'loading' })
  })

  it('stays loading on 401 until the unauthorized handler drops the token', () => {
    const me = { data: undefined, error: new ApiError(401, 'Токен истёк') }
    expect(resolveSessionState(input({ token: 't', me }))).toEqual({ kind: 'loading' })
  })

  it('is blocked on 403', () => {
    const me = { data: undefined, error: new ApiError(403, 'Пользователь заблокирован') }
    expect(resolveSessionState(input({ token: 't', me }))).toEqual({ kind: 'blocked' })
  })

  it('shows an error on a server failure and keeps the token', () => {
    const me = { data: undefined, error: new ApiError(500, 'Ошибка сервера') }
    expect(resolveSessionState(input({ token: 't', me }))).toEqual({
      kind: 'error',
      message: 'Ошибка сервера',
    })
  })

  it('shows a connection error when the network fails', () => {
    const me = { data: undefined, error: new TypeError('Failed to fetch') }
    expect(resolveSessionState(input({ token: 't', me }))).toEqual({
      kind: 'error',
      message: 'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.',
    })
  })
})

describe('resolveSessionState without a token', () => {
  it('sends a browser user to the login page', () => {
    expect(resolveSessionState(input())).toEqual({ kind: 'unauthenticated' })
  })

  it('sends a browser user to login even if stale /me data is cached', () => {
    expect(resolveSessionState(input({ me: { data: user, error: null } }))).toEqual({
      kind: 'unauthenticated',
    })
  })

  it('is loading inside Max while signing in with initData', () => {
    expect(resolveSessionState(input({ inMax: true }))).toEqual({ kind: 'loading' })
  })

  it('is blocked when Max sign-in returns 403', () => {
    const maxLogin = { error: new ApiError(403, 'Пользователь заблокирован') }
    expect(resolveSessionState(input({ inMax: true, maxLogin }))).toEqual({ kind: 'blocked' })
  })

  it('shows an error when initData is rejected', () => {
    const maxLogin = { error: new ApiError(401, 'Неверная подпись') }
    expect(resolveSessionState(input({ inMax: true, maxLogin }))).toEqual({
      kind: 'error',
      message: 'Неверная подпись',
    })
  })
})
```

- [ ] **Step 2: Запустить — должно упасть**

Run: `pnpm exec vitest run src/app/routes/session-state.test.ts`
Expected: FAIL — `Failed to resolve import "./session-state"`.

- [ ] **Step 3: `session-state.ts`**

```ts
import type { User } from '@/entities/user'
import { isApiError } from '@/shared/api'

export type SessionState =
  | { kind: 'loading' }
  | { kind: 'ready'; user: User }
  | { kind: 'unauthenticated' }
  | { kind: 'blocked' }
  | { kind: 'error'; message: string }

export interface SessionInput {
  token: string | null
  inMax: boolean
  me: { data: User | undefined; error: unknown }
  maxLogin: { error: unknown }
}

const NETWORK_ERROR = 'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.'

function errorMessage(error: unknown): string {
  return isApiError(error) ? error.message : NETWORK_ERROR
}

export function resolveSessionState({ token, inMax, me, maxLogin }: SessionInput): SessionState {
  if (token !== null && me.data) {
    return { kind: 'ready', user: me.data }
  }
  if (isApiError(me.error, 403) || isApiError(maxLogin.error, 403)) {
    return { kind: 'blocked' }
  }
  if (token !== null) {
    // 401 means the token is being dropped by the api client; wait for that.
    if (me.error && !isApiError(me.error, 401)) {
      return { kind: 'error', message: errorMessage(me.error) }
    }
    return { kind: 'loading' }
  }
  if (!inMax) {
    return { kind: 'unauthenticated' }
  }
  if (maxLogin.error) {
    return { kind: 'error', message: errorMessage(maxLogin.error) }
  }
  return { kind: 'loading' }
}
```

- [ ] **Step 4: Запустить — проходит**

Run: `pnpm exec vitest run src/app/routes/session-state.test.ts`
Expected: PASS (11 тестов).

- [ ] **Step 5: Тесты `home-path.test.ts`**

```ts
import { describe, expect, it } from 'vitest'
import type { User } from '@/entities/user'
import { homePathFor } from './home-path'

const user = (role: User['role']): User => ({
  id: 1,
  max_user_id: 1,
  first_name: 'Тест',
  last_name: null,
  username: null,
  phone: null,
  role,
})

describe('homePathFor', () => {
  it.each([
    ['ADMIN', '/staff'],
    ['MANAGER', '/staff'],
    ['CLIENT', '/client'],
  ] as const)('sends %s to %s', (role, path) => {
    expect(homePathFor(user(role))).toBe(path)
  })
})
```

- [ ] **Step 6: Запустить — должно упасть**

Run: `pnpm exec vitest run src/app/routes/home-path.test.ts`
Expected: FAIL — `Failed to resolve import "./home-path"`.

- [ ] **Step 7: `home-path.ts`**

```ts
import { isStaff, type User } from '@/entities/user'
import { routePaths } from '@/shared/config'

export function homePathFor(user: User): string {
  return isStaff(user) ? routePaths.staff : routePaths.client
}
```

- [ ] **Step 8: Запустить — проходит**

Run: `pnpm exec vitest run src/app/routes`
Expected: PASS (14 тестов).

- [ ] **Step 9: Гарды и роутер**

`SessionGate.tsx`:
```tsx
import { Button } from '@maxhub/max-ui'
import { useEffect } from 'react'
import { Navigate, Outlet } from 'react-router'
import { useMe, useSessionStore } from '@/entities/session'
import { useLoginByMax } from '@/features/auth-by-max'
import { routePaths } from '@/shared/config'
import { isInMax } from '@/shared/lib/max-bridge'
import { SplashScreen } from '@/shared/ui/splash-screen'
import { StatusScreen } from '@/shared/ui/status-screen'
import { resolveSessionState } from './session-state'

export function SessionGate() {
  const token = useSessionStore((state) => state.token)
  const me = useMe()
  const maxLogin = useLoginByMax()
  const { mutate: loginByMax, reset: resetMaxLogin } = maxLogin
  const inMax = isInMax()

  const shouldLoginByMax = inMax && token === null && !maxLogin.isPending && !maxLogin.isError
  useEffect(() => {
    if (shouldLoginByMax) {
      loginByMax()
    }
  }, [shouldLoginByMax, loginByMax])

  const state = resolveSessionState({
    token,
    inMax,
    me: { data: me.data, error: me.error },
    maxLogin: { error: maxLogin.error },
  })

  const retry = () => {
    if (token !== null) {
      void me.refetch()
    } else {
      // Clearing the error re-enables the effect above, which signs in again.
      resetMaxLogin()
    }
  }

  switch (state.kind) {
    case 'ready':
      return <Outlet />
    case 'unauthenticated':
      return <Navigate to={routePaths.login} replace />
    case 'loading':
      return <SplashScreen />
    case 'blocked':
      return (
        <StatusScreen
          title="Доступ ограничен"
          text="Ваш аккаунт заблокирован. Обратитесь в управляющую компанию."
        />
      )
    case 'error':
      return (
        <StatusScreen
          title="Не удалось войти"
          text={state.message}
          action={<Button onClick={retry}>Повторить</Button>}
        />
      )
  }
}
```

`RequireRole.tsx`:
```tsx
import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useMe } from '@/entities/session'
import type { User } from '@/entities/user'
import { routePaths } from '@/shared/config'

interface RequireRoleProps {
  allow: (user: User) => boolean
  children: ReactNode
}

export function RequireRole({ allow, children }: RequireRoleProps) {
  const { data: user } = useMe()
  if (!user) {
    return null
  }
  if (!allow(user)) {
    return <Navigate to={routePaths.home} replace />
  }
  return children
}
```

`RoleRedirect.tsx`:
```tsx
import { Navigate } from 'react-router'
import { useMe } from '@/entities/session'
import { homePathFor } from './home-path'

export function RoleRedirect() {
  const { data: user } = useMe()
  return user ? <Navigate to={homePathFor(user)} replace /> : null
}
```

`router.tsx`:
```tsx
import { createBrowserRouter } from 'react-router'
import { isClient, isStaff } from '@/entities/user'
import { ClientHomePage } from '@/pages/client-home'
import { LoginPage } from '@/pages/login'
import { NotFoundPage } from '@/pages/not-found'
import { StaffHomePage } from '@/pages/staff-home'
import { routePaths } from '@/shared/config'
import { AppShell } from '@/widgets/app-shell'
import { RequireRole } from './RequireRole'
import { RoleRedirect } from './RoleRedirect'
import { SessionGate } from './SessionGate'

export const router = createBrowserRouter([
  { path: routePaths.login, element: <LoginPage /> },
  {
    path: routePaths.home,
    element: <SessionGate />,
    children: [
      { index: true, element: <RoleRedirect /> },
      {
        path: routePaths.staff,
        element: (
          <RequireRole allow={isStaff}>
            <AppShell />
          </RequireRole>
        ),
        children: [{ index: true, element: <StaffHomePage /> }],
      },
      {
        path: routePaths.client,
        element: (
          <RequireRole allow={isClient}>
            <ClientHomePage />
          </RequireRole>
        ),
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])
```

- [ ] **Step 10: Провайдеры**

`providers/api-session.ts`:
```ts
import { useSessionStore } from '@/entities/session'
import { queryClient, setTokenGetter, setUnauthorizedHandler } from '@/shared/api'

setTokenGetter(() => useSessionStore.getState().token)

setUnauthorizedHandler(() => {
  useSessionStore.getState().clear()
  queryClient.clear()
})
```

`providers/ThemeProvider.tsx`:
```tsx
import { MaxUI } from '@maxhub/max-ui'
import { useLayoutEffect, type ReactNode } from 'react'
import { useColorScheme } from '@/shared/lib/color-scheme'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const colorScheme = useColorScheme()

  // Same scheme for Max UI and for Tailwind's dark: variant.
  useLayoutEffect(() => {
    document.documentElement.dataset.colorScheme = colorScheme
  }, [colorScheme])

  return <MaxUI colorScheme={colorScheme}>{children}</MaxUI>
}
```

`providers/AppProviders.tsx`:
```tsx
import { QueryClientProvider } from '@tanstack/react-query'
import { MotionConfig } from 'framer-motion'
import { RouterProvider } from 'react-router'
import { queryClient } from '@/shared/api'
import { router } from '../routes/router'
import { ThemeProvider } from './ThemeProvider'

export function AppProviders() {
  return (
    <ThemeProvider>
      <MotionConfig reducedMotion="user">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </MotionConfig>
    </ThemeProvider>
  )
}
```

`entrypoint/main.tsx` (полностью заменить временный код):
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '../styles/index.css'
import '../providers/api-session'
import { AppProviders } from '../providers/AppProviders'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders />
  </StrictMode>,
)
```

- [ ] **Step 11: Автопроверка**

Run: `bash scripts/check.sh`
Expected: `all checks passed`. `fsd/insignificant-slice` — остановиться и спросить.

- [ ] **Step 12: Ручная проверка в браузере**

Бэкенд поднят и засижен (Global Constraints). `pnpm dev`, открыть `http://localhost:5173`.

Проверить и записать результат по каждому пункту:
1. `/` → редирект на `/login`, видны три демо-пользователя.
2. «Анна — администратор» → `/staff`; на широком окне сайдбар с «Обращения», «Контент», «Пользователи» (два последних неактивны), имя и роль, «Выйти».
3. Окно уже 1024px → сайдбар скрыт, снизу таб-панель, сверху имя и «Выйти».
4. F5 → остаёмся на `/staff` без повторного входа.
5. «Выйти» → `/login`; в localStorage `uk-session` содержит `"token":null`.
6. «Игорь — менеджер» → `/staff`, пунктов «Контент»/«Пользователи» нет.
7. «Мария — клиент» → `/client` с текстом про бота; ввести в адресной строке `/staff` → возврат на `/client`.
8. Поле «Другой пользователь»: пусто/`abc` → «Войти» неактивна; `42` → «Пользователь не найден».
9. В DevTools испортить токен в `uk-session` → F5 → `/login` (без цикла, без экрана ошибки).
10. Войти, остановить бэкенд (`docker compose stop api`), F5 → «Не удалось войти» + «Повторить»; запустить (`docker compose start api`) → «Повторить» → `/staff`.
11. Переключить тему ОС светлая ↔ тёмная → фон и компоненты Max UI меняются вместе, без перезагрузки.
12. `/nope` → «Страница не найдена» → «На главную» работает.

Если какой-то пункт не выполняется — это баг Task 7 или раньше: исправить (через superpowers:systematic-debugging), повторить `check.sh` и пункт.

- [ ] **Step 13: Commit**

```bash
git add frontend/src/app
git commit -m "feat(web): wire session gate, role routing and theme"
```

---

### Task 8: Документация

**Files:**
- Modify: `AGENTS.md` (разделы «Стек», «Команды», «Правила → Frontend»), `docs/architecture.md` (раздел «Frontend»), `docs/plan.md` (Ф0/Ф1)

- [ ] **Step 1: `AGENTS.md`**

В «Стек» заменить строку фронтенда:
```markdown
- **Frontend:** TypeScript, React 19, Vite, Tailwind CSS v4, Max UI (`@maxhub/max-ui`), framer-motion, React Router v7, TanStack Query, Zustand, openapi-fetch; pnpm, ESLint, Prettier, Steiger, Vitest.
```

В «Команды» после блока бэкенда добавить:
````markdown
Фронтенд — из каталога `frontend/`:

```bash
# Первый запуск
cp .env.template .env
pnpm install

# Dev-сервер на http://localhost:5173; /api проксируется на http://localhost:8000
pnpm dev

# Тесты
pnpm test

# Перегенерировать типы API после изменения backend/openapi.json
pnpm gen:api

# Проверка перед вливанием в main: tsc, eslint, prettier, steiger, vitest, актуальность типов API, сборка
scripts/check.sh
```
````

В «Правила → Frontend» заменить `— (появятся после выбора стека)` на:
```markdown
Архитектура — Feature-Sliced Design строго по методичке; подробно — [docs/architecture.md](docs/architecture.md#frontend).

- Слои: `app → pages → widgets → features → entities → shared`; импорт только вниз. `processes` не используем.
- Кросс-импорт слайсов одного слоя запрещён; `@x` — только по согласованию.
- Снаружи слайса — только через его `index.ts`; внутри слайса — относительные импорты, между слайсами — через `@/`.
- В `app` и `shared` нет слайсов, только сегменты; сегмента `ui` в `app` нет.
- Сегменты по назначению: `ui`, `model`, `api`, `lib`, `config` — не `components`, `hooks`, `types`, `utils`.
- Steiger (`pnpm fsd`) зелёный; правила не отключать без согласования.
- `src/shared/api/schema.d.ts` — только `pnpm gen:api`, руками не править; при конфликте перегенерировать.
- Пользователь — только в кэше TanStack Query (`['me']`); в Zustand — токен и клиентские флаги.
- Компоненты — Max UI; Tailwind — раскладка и кастомные блоки. Цвет бренда — `--brand` / `bg-brand`.
- Тесты — Vitest на чистую логику рядом с кодом (`*.test.ts`); новая чистая логика — тест.
```

- [ ] **Step 2: `docs/architecture.md`, раздел «Frontend»**

Заменить строку `Стек: — (выбирает фронтенд-разработчик).` на:
```markdown
Стек: TypeScript, React 19, Vite, Tailwind CSS v4, Max UI, framer-motion, React Router v7, TanStack Query, Zustand, openapi-fetch. Архитектура — Feature-Sliced Design, контроль — Steiger. Дизайн фундамента — [спек](superpowers/specs/2026-09-26-frontend-foundation-design.md).

```
frontend/src/
├── app/        entrypoint, providers (тема, Query, роутер), routes (гарды, вход), styles
├── pages/      login, staff-home, client-home, not-found
├── widgets/    app-shell — адаптивный каркас сотрудника
├── features/   auth-by-max, auth-dev, logout
├── entities/   session (токен, /me), user (роли)
└── shared/     api (openapi-fetch + сгенерированные типы), config, lib/max-bridge, lib/color-scheme, ui
```

Вход:

1. Есть токен → `GET /me`: 200 — вход; 401 — токен сбрасывается; 403 — «Доступ ограничен»; сеть или 5xx — «Не удалось войти» с повтором, токен сохраняется.
2. Нет токена: в Max — `POST /auth/max` с `initData`; в браузере — `/login` (dev-вход при `VITE_DEV_AUTH=true`, иначе подсказка про `/panel`).
3. `/` ведёт по роли: `MANAGER`/`ADMIN` → `/staff`, `CLIENT` → `/client`.

Тема: схема из `prefers-color-scheme`, одна и та же для Max UI и Tailwind (`data-color-scheme` на `<html>`). Стили Max UI — в CSS-слое `maxui` между `base` и `utilities`, поэтому утилиты Tailwind перебивают их.
```

Остальные пункты раздела («Требования, которые от стека не зависят») оставить.

- [ ] **Step 3: `docs/plan.md`**

Заменить строки Ф0 и Ф1:
```markdown
- [x] **Ф0.** Стек, скелет, вход через `initData` (проверен на моке), тема.
- [ ] **Ф0.1.** Открытие в Max: живая проверка `initData`, `start_param` и темы. Нужен общий старт.
- [x] **Ф1.** Вход (`initData` / dev-вход), каркас, навигация по ролям, тема. Нужен Б2.
```

- [ ] **Step 4: Финальная проверка**

Run: `cd frontend && bash scripts/check.sh`
Expected: `all checks passed`.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md docs/architecture.md docs/plan.md
git commit -m "docs: describe frontend stack and conventions"
```
