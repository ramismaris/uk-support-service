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

```bash
git pull
docker compose up -d --build
```

Деплой с тега:

```bash
git fetch --tags
git checkout demo-N
docker compose up -d --build
```

Вернуться на `main` — `git checkout main`.

## Важно

- Пока бот запущен на сервере, локальные запуски должны идти с `BOT_MODE=off`: два процесса с одним токеном делят апдейты между собой, и часть сообщений теряется.
- Данные лежат в именованных томах. `docker compose down` их сохраняет, `docker compose down -v` удаляет базу, файлы и сертификаты.
