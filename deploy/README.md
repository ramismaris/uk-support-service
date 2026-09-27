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

Workflow `.github/workflows/deploy.yml` на каждый пуш в `main`, тег `demo-*` или ручной запуск (Actions → Deploy → Run workflow):

1. Прогоняет `backend/scripts/check.sh` и `frontend/scripts/check.sh`. Красные — деплоя нет.
2. Пуш в `main` и ручной запуск ждут одобрения в окружении `production`. Тег `demo-*` выкатывается сразу через окружение `demo`.
3. Заходит на сервер по SSH, переключает репозиторий на коммит и выполняет `docker compose up -d --build --wait`. Миграции применяет сам бэкенд при старте.

Настройка — один раз, в Settings репозитория на GitHub:

1. На сервере — отдельный ключ только для деплоя:

   ```bash
   ssh-keygen -t ed25519 -N "" -f ~/.ssh/deploy_uk -C github-deploy
   cat ~/.ssh/deploy_uk.pub >> ~/.ssh/authorized_keys
   cat ~/.ssh/deploy_uk        # → секрет SSH_PRIVATE_KEY
   ssh-keyscan -t ed25519 <хост>   # с любой машины; <хост> — как в SSH_HOST → секрет SSH_KNOWN_HOSTS
   ```

2. Secrets and variables → Actions → **Secrets**: `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `SSH_KNOWN_HOSTS`.
3. **Variables**: `DEPLOY_PATH` — путь к репозиторию на сервере, если не `/opt/uk-support-service`.
4. Environments → New environment `production` → Required reviewers — кто одобряет деплой из `main`. Окружение `demo` — без ограничений.
5. **Variables**: `DEPLOY_ENABLED=true`. До этого workflow только гоняет проверки и ничего не выкатывает: без настроенного `production` деплой ушёл бы без одобрения.

Заморозить сервер (например, на время демо) — `DEPLOY_ENABLED=false` или Actions → Deploy → Disable workflow.

## Важно

- Пока бот запущен на сервере, локальные запуски должны идти с `BOT_MODE=off`: два процесса с одним токеном делят апдейты между собой, и часть сообщений теряется.
- Данные лежат в именованных томах. `docker compose down` их сохраняет, `docker compose down -v` удаляет базу, файлы и сертификаты.
