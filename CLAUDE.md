# Dispatcher — память проекта (держать КОРОТКОЙ: грузится в каждый запрос)

FastAPI-диспетчерская заказов. Код: `backend/app/` (main.py, routers/, models/, db.py — SQLite через stdlib, security.py — пароли/токены, notify.py — Telegram, static/ — веб-панель на `/ui/`).
- Все эндпоинты, кроме `GET /` и `POST /auth/login`, требуют Bearer-токен; users и audit — только роль admin.
- База: `data/dispatcher.db` (в .gitignore, бэкап при каждом деплое). Новые зависимости не добавлять без нужды.
- Запуск: `cd backend && python run.py` (порт 8000)
- Тесты: `cd backend && python -m pytest -q`
- Деплой: push в `main` → GitHub Actions (`.github/workflows/deploy.yml`) → `deploy/deploy.sh` на сервере. HTTPS: `deploy/setup_https.sh <домен>`.
  Работа идёт в ветках `claude/*`, в main — только через PR после зелёного CI.

## Правила экономии токенов
- Не читать файлы целиком без нужды: сначала Grep/Glob, потом Read с offset/limit.
- Поиск по коду/разведка → агент `explorer` (haiku). Мелкие правки → `coder` (sonnet).
  Ревью → `reviewer` (sonnet). Деплой/логи CI → `deployer` (haiku). Opus — только архитектура.
- Отвечать кратко, без пересказа кода и диффов. Не повторять уже выясненное.
- Перед правкой — один раз прочитать нужный кусок; после правки не перечитывать.
- Названия файлов/модулей — латиницей (кириллица в именах файлов ломает импорты).
