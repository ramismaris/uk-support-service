# Деплой

Одна установка = одна УК = один бот. Стек: `db` (Postgres), `api` (бэкенд и бот в одном процессе), `web` (собранный фронт), `caddy` (HTTPS, `/api` → `api`, остальное → `web`).

## Что нужно

- Сервер с Docker и плагином `docker compose`.
- Домен, A-запись которого указывает на сервер.
- Открытые порты 80 и 443: Caddy сам получает HTTPS-сертификат.

## Первый запуск

```bash
git clone https://github.com/ramismaris/uk-support-service.git
cd uk-support-service/deploy
cp .env.template .env
```

Заполните `.env`:

- `DOMAIN` — ваш домен, например `uk.example.ru`.
- `BOT_TOKEN` — токен бота Max.
- `SECRET_KEY` — `openssl rand -hex 32`.
- `DATABASE_PASSWORD` — `openssl rand -hex 32`.
- `ADMIN_MAX_USER_IDS` — можно оставить пустым и выдать первого админа позже (см. ниже).

Пустой `DATABASE_PASSWORD` не даст запуститься Postgres, а `SECRET_KEY` короче 32 символов — приложению: ошибка видна сразу, а не превращается в слабый дефолт. `openssl rand -hex 32` даёт hex намеренно: `DATABASE_PASSWORD` подставляется в URL подключения без экранирования, и символы `/`, `@`, `+` сломали бы его.

```bash
docker compose up -d --build
```

Фронт собирается внутри образа `web`, Node на сервере не нужен.

## Проверка

```bash
curl https://<домен>/api/v1/health
# {"status":"ok"}

docker compose ps
docker compose logs -f api
```

## Демо-данные

```bash
docker compose exec api python scripts/seed.py
```

## Первый админ

Напишите боту `/id` — он пришлёт ваш `max_user_id`. Впишите его в `ADMIN_MAX_USER_IDS` в `.env` (несколько — через запятую) и примените:

```bash
docker compose up -d
```

Роль выдаётся при следующем сообщении боту или следующем входе.

## Фронтенд

`frontend/Dockerfile` собирает SPA и раздаёт его своим Caddy на порту 80 внутри сети. Файлы из `assets/` с хэшем в имени кэшируются на год, остальное — с `no-cache`, поэтому после обновления браузер сразу берёт новую версию.

Экран dev-входа в прод-сборке выключен. Для демо без Max его можно включить: `DEV_AUTH=true` и `VITE_DEV_AUTH=true` в `.env`, затем `docker compose up -d --build`.

## Мини-приложение Max

Адрес мини-приложения — `https://<домен>/`.

## Обновление

Обычно — автодеплоем из GitHub Actions (ниже). Вручную:

```bash
git fetch --tags
git checkout --detach origin/main   # или тег: git checkout demo-N
cd deploy
docker compose up -d --build
```

Автодеплой выкатывает конкретный коммит, поэтому репозиторий на сервере стоит на отсоединённом HEAD — это нормально.

## Автодеплой

Workflow `.github/workflows/deploy.yml`:

- пуш в `main` — только проверки (`backend/scripts/check.sh` и `frontend/scripts/check.sh`);
- ручной запуск на `main` — Actions → Deploy → Run workflow: проверки, затем выкатка. Запуск на другой ветке только гоняет проверки;
- тег `demo-*` — проверки и сразу выкатка.

Красные проверки — выкатки нет. Выкатка: SSH на сервер, репозиторий переключается на коммит, образы собираются, пока работает старая версия. Затем заменяются только `api` и `web`, а `db` и `caddy` продолжают работать; Caddy перечитывает `Caddyfile` командой `caddy reload`. В конце — ожидание ответа `/api/v1/health` до 5 минут. Миграции применяет сам бэкенд при старте.

Без простоя: пока `api` и `web` поднимаются, Caddy не отвечает 502, а до 30 секунд повторяет подключение (`lb_try_duration` в `Caddyfile`) — запрос просто дольше ждёт. WebSocket переподключается сам. Два `api` одновременно не запускаем: в том же процессе бот, а два процесса с одним токеном делят апдейты.

`api` и `web` удаляются и создаются заново, а не пересоздаются: так деплой работает и со старым `docker-compose` v1, который на свежем Docker падает при пересоздании (`KeyError: 'ContainerConfig'`).

Откат — ручной запуск на теге `demo-*` с нужной версией (Run workflow → Use workflow from → Tags).

Настройка — один раз:

1. На сервере — отдельный ключ только для деплоя:

   ```bash
   ssh-keygen -t ed25519 -N "" -f ~/.ssh/deploy_uk -C github-deploy
   cat ~/.ssh/deploy_uk.pub >> ~/.ssh/authorized_keys
   cat ~/.ssh/deploy_uk        # → секрет SSH_PRIVATE_KEY
   ssh-keyscan -t ed25519 <хост>   # <хост> — как в SSH_HOST → секрет SSH_KNOWN_HOSTS
   ```

2. GitHub → Settings → Secrets and variables → Actions → **Secrets**: `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `SSH_KNOWN_HOSTS`.
3. **Variables**: `DEPLOY_PATH` — путь к репозиторию на сервере, если не `/opt/uk-support-service`.

Заморозить сервер (например, на время демо) — Actions → Deploy → Disable workflow.

## Важно

- Пока бот запущен на сервере, локальные запуски должны идти с `BOT_MODE=off`: два процесса с одним токеном делят апдейты между собой, и часть сообщений теряется.
- Данные лежат в именованных томах. `docker compose down` их сохраняет, `docker compose down -v` удаляет базу, файлы и сертификаты.
