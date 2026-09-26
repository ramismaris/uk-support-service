# Фронтенд: фундамент (Ф0 + Ф1)

Первый подпроект фронтенда: скелет SPA, вход, каркас с навигацией по ролям, тема. Экраны обращений (Ф2+) — отдельными спеками, когда бэкенд закроет Б3 и дальше.

Контекст: [product.md](../../product.md), [architecture.md](../../architecture.md#frontend), [plan.md](../../plan.md#фронтенд).

## Цель и критерии готовности

- `pnpm dev` + бэкенд с `DEV_AUTH=true`: вход под любым из трёх сид-пользователей (админ `1000001`, менеджер `1000002`, клиент `1000003`) ведёт в свою ветку; выход работает; после перезагрузки сессия сохраняется.
- Светлая и тёмная тема переключаются вслед за системой (в Max — за клиентом).
- `frontend/scripts/check.sh` зелёный; `pnpm build` кладёт сборку в `frontend/dist`, откуда её раздаёт Caddy (`deploy/docker-compose.yml`).
- Вход через Max (`initData`) реализован и покрыт тестами на моке `window.WebApp`. Живая проверка в Max — после регистрации мини-приложения на домене (общий старт), отдельный пункт в `plan.md`.

## Стек

| Что | Выбор |
|---|---|
| Сборка | Vite, pnpm |
| Язык, UI | TypeScript (strict), React 19 |
| Компоненты | `@maxhub/max-ui` |
| Стили | Tailwind CSS v4 |
| Анимации | framer-motion |
| Роутинг | React Router v7, `createBrowserRouter` |
| Серверное состояние | TanStack Query |
| Клиентское состояние | Zustand |
| Контракт API | `openapi-typescript` (типы) + `openapi-fetch` (клиент) |
| Качество | ESLint, Prettier, Steiger, Vitest |

dnd-kit в этом подпроекте не ставим.

## Архитектура: Feature-Sliced Design

Строго по методичке FSD 2.x:

- Слои: `app → pages → widgets → features → entities → shared`. Слой `processes` не используем (устарел).
- Импорт только в нижележащие слои. Кросс-импорт между слайсами одного слоя запрещён; нотация `@x` — только если без неё не обойтись, по согласованию.
- Каждый слайс отдаёт наружу только `index.ts` (public API); импорт во внутренние файлы чужого слайса запрещён.
- В `app` и `shared` слайсов нет, только сегменты.
- Сегменты по назначению: `ui`, `model`, `api`, `lib`, `config`.
- Алиас `@/` → `src/`.
- Соблюдение проверяет Steiger.

```
frontend/
├── index.html                подключает https://st.max.ru/js/max-web-app.js
├── vite.config.ts            алиас @/, прокси /api → http://localhost:8000
├── scripts/check.sh
└── src/
    ├── app/
    │   ├── entrypoint/       main.tsx
    │   ├── providers/        MaxUI + схема темы, QueryClientProvider, RouterProvider
    │   ├── routes/           router.tsx, bootstrap сессии, гарды по ролям
    │   └── styles/           index.css: tailwind, стили max-ui, --brand
    ├── pages/
    │   ├── login/            вход в браузере
    │   ├── staff-home/       заглушка «Обращения» (место для Ф2)
    │   ├── client-home/      заглушка «Заявки подаются в чате с ботом» (место для Ф7)
    │   └── not-found/
    ├── widgets/
    │   └── app-shell/        адаптивный каркас сотрудника
    ├── features/
    │   ├── auth-by-max/      обмен initData на токен
    │   ├── auth-dev/         dev-вход по max_user_id
    │   └── logout/
    ├── entities/
    │   ├── session/          токен (Zustand + persist), useMe()
    │   └── user/             UserRole, имя для отображения, isStaff/isAdmin
    └── shared/
        ├── api/              schema.d.ts (генерируется), клиент openapi-fetch, queryClient
        ├── config/           env, пути роутов
        ├── lib/max-bridge/   isInMax(), getInitData(), getStartParam()
        └── ui/               общие обёртки поверх Max UI — только по необходимости
```

### Разделение `session` и `user`

- `entities/session` владеет токеном и запросом `/me`: `useSessionStore` (token, setToken, clear) и `useMe()` (TanStack Query, ключ `['me']`).
- `entities/user` — доменная модель пользователя: хелперы ролей и отображения над типом `UserResponse` из `shared/api`.
- Друг друга они не импортируют; связывают их `features`, `widgets`, `app`.
- Пользователь в Zustand не копируется: единственный источник — кэш Query.

## `shared/api`

- `pnpm gen:api`: `openapi-typescript ../backend/openapi.json -o src/shared/api/schema.d.ts`. Файл коммитится; при конфликте — перегенерировать, руками не мёржить.
- Клиент `openapi-fetch` с `baseUrl: ''` (пути в схеме уже начинаются с `/api/v1`).
- Middleware подставляет `Authorization: Bearer <token>`. `shared` не импортирует `entities`, поэтому токен клиент берёт через геттер, а на 401 вызывает обработчик; оба регистрирует `app/providers` при старте (`setTokenGetter`, `setUnauthorizedHandler`). Обработчик чистит сессию и кэш Query.
- `queryClient` создаётся здесь же; `retry` для 401/403 выключен.

## `shared/lib/max-bridge`

Тонкая обёртка над `window.WebApp` из официального скрипта Max:

- `isInMax()` — `window.WebApp` есть и `initData` непустой;
- `getInitData()` — строка `initData`;
- `getStartParam()` — `initDataUnsafe.start_param`, если есть. В Ф1 значение только читается; переход на обращение по кнопке «Открыть» — в Ф2, когда бэкенд зафиксирует формат payload (Б3).

Тип `window.WebApp` описываем сами в `max-bridge` в объёме используемых полей.

## Вход и сессия

Bootstrap выполняется в корне роутера перед рендером защищённых веток; пока идёт — сплэш.

1. Есть токен → `GET /api/v1/me`.
   - 200 → пользователь в кэше Query, рендер по роли.
   - 401 → токен сбрасывается, переход к шагу 2.
   - 403 (заблокирован) → экран «Доступ ограничен», без повтора.
2. Токена нет:
   - в Max → `POST /api/v1/auth/max { init_data }` → токен в стор, `user` из ответа — в кэш `['me']`. Ошибка → экран «Не удалось войти» с кнопкой «Повторить»; 403 → «Доступ ограничен».
   - в браузере → редирект на `/login`.

Токен хранится в localStorage (Zustand `persist`) в обоих режимах.

### Страница `/login` (только браузер)

- `VITE_DEV_AUTH=true`: три кнопки сид-пользователей (Анна — админ, Игорь — менеджер, Мария — клиент) и поле для произвольного `max_user_id` → `POST /api/v1/auth/dev`.
- Иначе: «Напишите боту `/panel`, чтобы получить ссылку для входа». Сам вход по ссылке — Ф8 (нужен Б9).
- Если пользователь уже вошёл — редирект на `/`.

### Выход

`POST /api/v1/auth/logout` → очистка стора и кэша Query → `/login`. Кнопка есть только в браузере: в Max вход автоматический.

## Роуты

| Путь | Доступ | Экран |
|---|---|---|
| `/login` | публичный | вход |
| `/` | вошедший | редирект по роли: `MANAGER`/`ADMIN` → `/staff`, `CLIENT` → `/client` |
| `/staff` | `MANAGER`, `ADMIN` | app-shell + staff-home |
| `/client` | `CLIENT` | client-home, полноэкранно, без app-shell |
| `*` | все | not-found |

Гард ветки пускает только свою роль; чужую роль отправляет на `/`.

## Каркас (`widgets/app-shell`)

Адаптивный, один код:

- узкий экран (< `lg`): контент во весь экран, нижняя таб-панель;
- широкий (≥ `lg`): боковое меню слева, контент справа. В Ф2 контент станет master-detail (список + карточка).

Пункты меню задаются конфигом в слайсе с признаком роли. В Ф1 есть «Обращения» (активный) и для `ADMIN` — «Контент», «Пользователи» как неактивные пункты: их роуты появятся в Ф5. В шапке или сайдбаре — имя пользователя и, в браузере, «Выйти».

## Тема

- Схему (светлая/тёмная) определяет провайдер `MaxUI`: в Max — по клиенту, в браузере — по `prefers-color-scheme`. `app/providers` вычисляет схему из того же источника, передаёт её в `MaxUI` явно и ставит атрибут `data-color-scheme` на `<html>`. Так Max UI и Tailwind не разъезжаются.
- Tailwind v4: `@custom-variant dark ([data-color-scheme="dark"] &)`.
- Роли: Max UI — кнопки, поля, типографика, списки; Tailwind — раскладка, отступы, кастомные блоки. Каскад: стили Max UI импортируются в собственный слой — `@layer theme, base, maxui, components, utilities;` и `@import "@maxhub/max-ui/dist/styles.css" layer(maxui);`. Так preflight не ломает компоненты, а утилиты Tailwind в `className` перебивают стили Max UI. Без слоя стили Max UI победили бы любые утилиты. Проверяется на первом экране.
- Основной цвет — CSS-переменная `--brand` с дефолтным значением. Значение и логотип из `THEME` подставляются в Ф11 (нужен Б6).
- framer-motion: только переходы между экранами и появление сплэша.

## Тесты и проверка

Vitest, окружение `jsdom`, только чистая логика:

- `max-bridge`: режим, `initData`, `start_param` при разных моках `window.WebApp` (нет объекта, пустой `initData`, полный);
- `entities/user`: `isStaff`, `isAdmin`, имя для отображения;
- редирект по роли (`/` → `/staff` | `/client`) — чистая функция в `app/routes`;
- middleware `shared/api`: подстановка токена, вызов обработчика на 401.

UI-тестов в этом подпроекте нет.

`frontend/scripts/check.sh` — по аналогии с `backend/scripts/check.sh`:

```bash
pnpm exec tsc --noEmit
pnpm exec eslint .
pnpm exec prettier --check .
pnpm exec steiger ./src
pnpm exec vitest run
# schema.d.ts актуален: генерация во временный файл и сравнение
pnpm build
```

## Документация в том же изменении

- `AGENTS.md`: стек фронтенда, раздел «Frontend» в правилах (FSD, public API, запрет кросс-импортов, Steiger, генерация `schema.d.ts`), команды фронтенда.
- `docs/architecture.md`: раздел «Frontend» — структура, поток входа, тема.
- `docs/plan.md`: отметить Ф0/Ф1; живую проверку `initData` в Max — отдельным открытым пунктом.

## Вне рамок

Экраны обращений, WebSocket, переход по кнопке «Открыть» на обращение, вход по одноразовой ссылке `/panel`, брендинг из `THEME`, редактор контента и пользователи, dnd-kit.
