# AGENTS.md

Сервис обращений жильцов для управляющей компании (УК). Клиентская часть — бот в мессенджере Max; сотрудники работают в мини-приложении Max или в веб-панели (одно SPA). Проект хакатонный: приоритет — работающий демо-сценарий, а не полнота.

## Документация — прочитать перед работой

- [docs/product.md](docs/product.md) — роли, функции, скоуп (Must / Should / не делаем)
- [docs/architecture.md](docs/architecture.md) — слои, структура, провайдеры, авторизация, тесты, конфигурация
- [docs/data-model.md](docs/data-model.md) — таблицы и поля
- [docs/ticket-lifecycle.md](docs/ticket-lifecycle.md) — статусы, переходы, маршрутизация сообщений, уведомления
- [docs/plan.md](docs/plan.md) — план реализации и трекер: этапы бэкенда и фронтенда
- `raw_data/` — исходные заметки; не редактировать, при расхождении права `docs/`

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, `maxapi`, PostgreSQL; uv, ruff, pytest.
- **Frontend:** — (выбирает фронтенд-разработчик)

## Структура репозитория

```
backend/    API + бот, один процесс
frontend/   SPA: мини-приложение и веб-панель
deploy/     docker compose, Caddy
docs/       документация проекта
raw_data/   исходные заметки
```

## Команды

Все команды — из каталога `backend/`.

```bash
# Первый запуск
cp .env.template .env
docker compose up -d --wait db
uv sync
uv run alembic upgrade head

# API в режиме разработки; Swagger — /docs при DEBUG=true
uv run uvicorn src.main:app --reload

# Тесты
uv run pytest

# Проверка перед вливанием в main: ruff, pytest, актуальность openapi.json, одна «голова» Alembic
scripts/check.sh

# Перегенерировать openapi.json после изменений API
uv run python scripts/dump_openapi.py

# Демо-данные (идемпотентно: добавляет только отсутствующие строки)
uv run python scripts/seed.py
docker compose exec api python scripts/seed.py

# Новая миграция
uv run alembic revision --autogenerate -m "..."

# Весь бэкенд (API + Postgres) в Docker одной командой
docker compose up -d --build
```

Бот по умолчанию выключен (`BOT_MODE=off`) — для фронтенд-разработки и тестов. Чтобы включить его, задайте в `.env` `BOT_MODE=polling` и `BOT_TOKEN`.

## Правила

### Общие

- Код, идентификаторы, комментарии, сообщения коммитов — на английском. Документация, тексты бота и интерфейса — на русском.
- Не выходить за рамки задачи. Функции вне Must/Should из `docs/product.md` не добавлять без согласования.
- Изменил модель данных, статусы или правила — обнови `docs/` в том же изменении.
- Секреты — только через `.env`; в репозитории лежит `.env.template`.
- Не добавлять фичи, рефакторинг и улучшения сверх задачи.
- Не добавлять обработку ошибок для сценариев, которые не могут произойти.
- Не создавать абстракции для одноразовых операций.
- Валидация только на границах системы: входящие запросы, апдейты Max, внешние API.

### Backend

Структура и паттерны — как в `arendalike-api`; подробно — [docs/architecture.md](docs/architecture.md).

- Слои: API и бот → services → repositories; внешний мир — через `providers/`.
- API-роутеры и хендлеры бота: валидация, вызов сервисов, ответ. Без бизнес-логики и без запросов к БД.
- Зависимости FastAPI — через `Annotated[..., Depends(...)]`, а не значением по умолчанию: ruff 0.16 включает правило B008.
- Services: вся бизнес-логика и транзакции. Не импортируют FastAPI и `maxapi` — принимают обычные типы, потому что их вызывают и API, и бот. Ошибки — наследники `AppException` из `core/exceptions.py`.
- Repositories: CRUD и запросы SQLAlchemy, без бизнес-логики и без `commit`.
- Чистые правила (переходы статусов, маршрутизация сообщений, права) — только в `services/ticket_rules.py`; роутеры, хендлеры и другие сервисы их вызывают, а не дублируют.
- Providers: абстрактный класс + реализации + выбор в `providers/factory.py`. Сервисы зависят от абстракции.
- Фоновая работа — через `core/background.py`, не через `BackgroundTasks` FastAPI.
- Перечисления — `StrEnum` в `core/constants.py`, значения прописными (`IN_PROGRESS`).
- Автор действия (`created_by`, `changed_by_id`, `author_id`) — всегда из токена, никогда из тела запроса.
- Гонки (взятие обращения в работу, смена статуса) — блокировка строки через `with_for_update()`.
- Схема БД меняется только миграциями Alembic; autogenerate проверять глазами.
- Pydantic-схемы API отдельно от ORM-моделей.
- Тексты бота и уведомлений — в `core/texts.py`; тексты, которые правит админ, — в `content_blocks`.
- Тесты — зеркально `src/`: юнит-тесты сервисов с замоканными репозиториями и провайдерами, интеграционные — через API на тестовой БД. Новая бизнес-логика — юнит-тест; новый эндпоинт — интеграционный тест. `pytest` и `ruff` зелёные перед вливанием в `main`.

### Frontend

— (появятся после выбора стека)

### Контракт API

Бэкенд меняет схемы или роуты → перегенерирует `openapi.json` в том же коммите → фронт обновляется по нему. Об изменении API, которым фронт уже пользуется, — сообщить второму разработчику.

### Git

PR и ревью не используем: ветка вливается в `main` напрямую. `main` всегда в рабочем состоянии.

- Ветки: `<тип>/<кратко>` — `feat/bot-ticket-form`, `fix/status-card-edit`. Типы: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`. Ветка живёт недолго.
- Коммиты — Conventional Commits на английском: `feat(bot): add ticket form`. Области: `bot`, `api`, `services`, `db`, `web`, `deploy`, `docs`.
- Сообщение коммита — только заголовок: без описания и без трейлеров (`Co-Authored-By` и другой атрибуции агентов).
- Вливание — rebase и fast-forward, история линейная:

  ```bash
  git switch main && git pull
  git switch <branch> && git rebase main
  backend/scripts/check.sh
  git switch main && git merge --ff-only <branch> && git push
  git branch -d <branch>
  ```

- Проверки перед вливанием — локально; CI нет.
- `push --force` в `main` запрещён.
- Генерируемые файлы при конфликте руками не мёржить: `openapi.json` перегенерировать; при двух «головах» Alembic поправить `down_revision` у более поздней миграции.
- Перед демо — тег `demo-N`, деплой с тега.

### Агенты

- Работают в своей ветке или worktree. В `main` сами не вливают — вливает человек, прочитав изменения.
- Не делают force-push и не переписывают чужие ветки.
