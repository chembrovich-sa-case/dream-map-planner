# 🚀 Бэкенд сервиса «Горизонт» (Dream Map Planner API)

Архитектурная серверная часть проекта **«Горизонт»**, разработанная на современном стеке **Python 3.10+**, **FastAPI**, **SQLAlchemy 2.0** и **Pydantic v2** с поддержкой реляционной базы данных **PostgreSQL** (схема в 3-й нормальной форме 3NF).

---

## 🏗 Архитектура и структура каталога `backend/`

```
backend/
├── main.py              # Точка входа приложения FastAPI, CORS, обработка lifespan и /api/health
├── database.py          # Подключение к PostgreSQL через SQLAlchemy, сессии и авто-сидер данных
├── models.py            # Реляционные ORM-модели (users, life_spheres, goal_cards, goal_steps, fx)
├── schemas.py           # Pydantic-схемы валидации входящих/исходящих данных (DTO)
├── requirements.txt     # Зависимости проекта (FastAPI, Uvicorn, SQLAlchemy, Psycopg2 и др.)
├── README.md            # Руководство разработчика и инструкция по запуску
└── routers/             # Модульные эндпоинты RESTful API
    ├── __init__.py
    ├── auth.py          # Аутентификация, профиль и ролевая модель RBAC (admin / user / guest)
    ├── spheres.py       # Управление сферами жизни и колесом баланса (UC-3)
    ├── goals.py         # Карточки целей, чек-листы и динамический пересчет прогресса (UC-1, UC-2, UC-5)
    ├── currency.py      # Интеграция с официальным API курсов валют Нацбанка РБ (НБРБ)
    └── analytics.py     # Исторические срезы баланса (balance_snapshots) и аналитические ряды Chart.js
```

---

## 📋 Системные требования

* **Python:** 3.10 или новее
* **База данных:** PostgreSQL 14+ (или SQLite для легковесного локального тестирования)
* **Менеджер пакетов:** `pip`

---

## ⚡ Инструкция по быстрому запуску

### Шаг 1: Создание и активация виртуального окружения

В терминале перейдите в папку `backend/`:

```powershell
cd d:\Antigravity\Horizont\backend

# Создание виртуального окружения
python -m venv venv

# Активация на Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Либо на Windows (CMD):
venv\Scripts\activate.bat

# На Linux / macOS:
source venv/bin/activate
```

### Шаг 2: Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 3: Настройка базы данных

#### Вариант А: PostgreSQL (Рекомендуемый для продакшена)

1. Убедитесь, что служба PostgreSQL запущена.
2. Создайте базу данных `horizont_db` через `psql` или pgAdmin:
   ```sql
   CREATE DATABASE horizont_db;
   ```
3. *(Опционально)* Накатите готовую схему и триггеры из корня проекта:
   ```bash
   psql -U postgres -d horizont_db -f ../database/schema.sql
   ```
4. Укажите переменную окружения `DATABASE_URL` (например, в PowerShell):
   ```powershell
   $env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/horizont_db"
   ```

#### Вариант Б: SQLite (Мгновенный локальный запуск без сторонних служб)

Если PostgreSQL не установлен, сервер может работать на встроенном SQLite файле:
```powershell
$env:DATABASE_URL="sqlite:///./horizont.db"
```
*(При первом запуске SQLAlchemy автоматически создаст все необходимые таблицы и наполнит их начальными демонстрационными сферами, целями и демо-аккаунтами).*

---

### Шаг 4: Запуск сервера FastAPI через Uvicorn

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

После запуска в консоли появится сообщение:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
🚀 Запуск сервера «Горизонт» FastAPI...
✅ База данных успешно инициализирована демо-данными!
```

---

## 📖 Интерактивная документация API (Swagger / OpenAPI)

FastAPI автоматически строит и валидирует интерактивную спецификацию REST API:

* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
  *(Позволяет тестировать любые эндпоинты прямо из браузера через кнопку «Try it out»)*
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **OpenAPI Schema (JSON):** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 🛠 Ключевые группы эндпоинтов (API Contract)

### 1. Проверка работоспособности
* `GET /api/health` — мониторинг статуса сервера и связи с БД.

### 2. Авторизация и ролевой доступ (RBAC: UC-4 & Login Wall)
* `GET /api/auth/demo-users` — список готовых демо-аккаунтов (Администратор и Пользователь).
* `POST /api/auth/login` — вход в систему и получение токена доступа (принимает `admin`, `user` или email с паролем).
* `GET /api/auth/me` — профиль текущего пользователя.

### 3. Сферы жизни и Колесо баланса (UC-3)
* `GET /api/spheres` — получение всех сфер с рассчитанными баллами для радарной диаграммы.
* `POST /api/spheres` — создание новой сферы (доступно роли `admin`).
* `PUT /api/spheres/{id}` — редактирование параметров сферы.
* `DELETE /api/spheres/{id}` — каскадное удаление сферы.

### 4. Карточки целей и Чек-листы (UC-1, UC-2, UC-5)
* `GET /api/goals` — витрина целей с фильтрами по сфере (`sphere_id`), статусу (`status`) и поиску.
* `POST /api/goals` — добавление новой цели с шагами декомпозиции.
* `GET /api/goals/{id}` — детальный просмотр карточки цели со всеми шагами чек-листа (UC-5).
* `PUT /api/goals/{id}` — обновление параметров цели.
* `DELETE /api/goals/{id}` — удаление цели с пересчетом балла сферы.
* `PATCH /api/goals/{id}/steps/{step_id}/toggle` — интерактивная отметка выполнения шага (UC-2) с мгновенным пересчетом процента выполнения цели и общего колеса баланса.

### 5. Интеграция с Нацбанком РБ (НБРБ)
* `GET /api/currency/rates` — получение актуального курса USD/BYN с суточным кэшированием.
* `POST /api/currency/refresh` — принудительный опрос API `api.nbrb.by`.

### 6. Срезы баланса жизни и аналитика (balance_snapshots)
* `POST /api/snapshots` — сохранение текущего среза баланса жизни с автоматическим расчетом индекса гармонии и JSON-словаря баллов.
* `GET /api/snapshots` — получение истории срезов за период (`month`, `quarter`, `year`, `all`).
* `GET /api/snapshots/trend` — подготовленные агрегированные ряды для Chart.js (кривая гармонии % и баллы сфер во времени).
* `DELETE /api/snapshots/{id}` — удаление снимка баланса.
* `POST /api/currency/convert` — конвертация бюджетов целей между BYN и USD.

### 6. Аналитика и Исторические срезы баланса (balance_snapshots)
* `POST /api/analytics/snapshots` — создание точки фиксации среза колеса баланса в БД с авто-расчетом индекса гармонии.
* `GET /api/analytics/snapshots` — получение истории замеров за указанный период (`days`).
* `GET /api/analytics/trend` — готовый временной ряд для построения графиков динамики в Chart.js.
* `DELETE /api/analytics/snapshots/{id}` — удаление среза баланса.
