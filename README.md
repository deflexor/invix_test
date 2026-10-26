# Каталог товаров: Telegram Mini App

Минимальный сервис товаров: Telegram-бот с Mini App-каталогом, API на FastAPI и фронтенд на Next.js.

## Стек

- **Backend**: FastAPI + asyncpg, бот — aiogram 3.x (менеджер пакетов — `uv`)
- **Фронтенд**: Next.js (App Router)
- **БД**: PostgreSQL (по умолчанию — локальный контейнер в docker-compose)
- **S3**: MinIO (образы товаров)
- **Code quality**: backend — `ruff` (lint + format) и `mypy --strict`; frontend — `tsc --noEmit` и [Biome](https://biomejs.dev/)

## Структура

```
backend/            FastAPI + бот (uv-проект)
  app/main.py       HTTP API: список товаров, отдача картинок
  app/bot.py        Telegram-бот: каталог + создание товара админом
  app/db.py         Запросы к PostgreSQL (asyncpg)
  app/s3.py         Загрузка/скачивание картинок в MinIO
  app/config.py     Типизированные настройки из .env
  schema.sql        DDL таблицы products
frontend/           Next.js: страница «Каталог» (src/app/page.tsx)
docker-compose.yml  PostgreSQL + MinIO для локальной разработки
```

## Запуск

### 1. Инфраструктура

```bash
docker compose up -d
docker compose exec -T postgres psql -U catalog -d catalog < backend/schema.sql
```

Поднимаются PostgreSQL (порт 5432) и MinIO (9000, консоль — 9001) с бакетом `products`.

### 2. Backend

```bash
cd backend
cp .env.example .env        # затем заполните реальные значения
uv sync
uv run uvicorn app.main:app --port 8000   # API
uv run python -m app.bot                  # бот (в отдельном терминале)
```

Обязательные переменные `backend/.env`: `DATABASE_URL`, `S3_*`, `TELEGRAM_BOT_TOKEN`, `MINIAPP_URL`, `PUBLIC_API_URL` и `TELEGRAM_ADMIN_IDS` (Telegram ID администраторов через запятую — их можно узнать у @userinfobot). Пример готового `.env` уже лежит в `backend/`.

### 3. Фронтенд

```bash
cd frontend
cp .env.example .env.local   # API_URL=http://localhost:8000
npm install
npm run dev
```

Каталог: http://localhost:3000 — открывается и в обычном браузере, и внутри Telegram как Mini App.

### 4. Mini App для Telegram

Кнопка бота открывает только **https**-URL. Для локальной проверки опубликуйте фронтенд через туннель (ngrok/cloudflared: `ngrok http 3000`) и пропишите полученный `https://...`-адрес в `MINIAPP_URL`, а адрес API — в `PUBLIC_API_URL` (он используется для построения ссылок на картинки).

> Если `api.telegram.org` недоступен из вашей сети (бот падает с `Cannot connect to host api.telegram.org`), укажите прокси: `TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080` или `http://...`.

## Как пользоваться

- **Пользователь**: `/start` или любое сообщение → бот отвечает «У меня есть товар» и даёт кнопку «Открыть каталог» (Mini App).
- **Администратор** (ID из `TELEGRAM_ADMIN_IDS`): команда `/create_product`, затем одно сообщение с **фото и подписью** — подпись становится названием товара; фото кладётся в MinIO, запись — в PostgreSQL.

## Отказоустойчивость (stateless)

Каждый компонент не хранит состояния и может запускаться в нескольких экземплярах:

- **API** — без сессий и кэшей; каждый запрос читает PostgreSQL/MinIO. Масштабируется за балансировщиком без ограничений.
- **Бот** — без FSM и памяти: каждый апдейт обрабатывается независимо. В режиме long polling (`TELEGRAM_WEBHOOK_URL` не задан) запускается один экземпляр; для горизонтального масштабирования задайте `TELEGRAM_WEBHOOK_URL`

