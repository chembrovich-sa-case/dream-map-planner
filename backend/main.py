"""
Точка входа FastAPI приложения «Горизонт» (Dream Map Planner Backend).
Включает CORS-мидлвар, роутеры, Swagger-документацию и проверку здоровья.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import engine, get_db, init_db
from schemas import HealthResponse
from routers import auth, spheres, goals, currency, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Жизненный цикл приложения: инициализация БД и таблиц при старте.
    """
    print("🚀 Запуск сервера «Горизонт» FastAPI...")
    try:
        init_db()
    except Exception as e:
        print(f"⚠️ Ошибка автоматической инициализации БД: {e}")
    yield
    print("🛑 Остановка сервера «Горизонт»...")


# Описание тегов для интерактивной документации Swagger
tags_metadata = [
    {
        "name": "Health",
        "description": "Проверка состояния работоспособности сервера и связи с БД."
    },
    {
        "name": "Authentication & RBAC",
        "description": "Аутентификация, профиль пользователя и ролевая модель доступа (admin / user / guest)."
    },
    {
        "name": "Life Spheres (Баланс)",
        "description": "Управление сферами жизни, целевыми и текущими баллами колеса баланса."
    },
    {
        "name": "Goals & Dreams (Цели)",
        "description": "Витрина карточек целей, декомпозиция шагов, чек-листы и мгновенный пересчет прогресса."
    },
    {
        "name": "Currency & FX (НБРБ)",
        "description": "Официальные курсы валют Нацбанка РБ (BYN/USD), суточный кэш и конвертация."
    },
    {
        "name": "Analytics & Balance Snapshots (История и срезы)",
        "description": "Срезы баланса жизни во времени (balance_snapshots), расчет индекса гармонии и исторические тренды."
    }
]

app = FastAPI(
    title="Горизонт — Dream Map Planner API",
    description="""
# 🎯 Архитектурный REST API бэкенда «Горизонт»

Серверная часть платформы для визуализации карты желаний, декомпозиции целей и гармонизации колеса баланса жизни:

* **🔐 Авторизация и RBAC:** Разделение прав доступа (Администратор CMS vs Пользователь).
* **⚖️ Колесо баланса:** 6 базовых сфер жизни с динамическим пересчетом баллов.
* **📋 Цели и Чек-листы:** Интерактивное управление шагами с весовыми коэффициентами.
* **🇧🇾 Мультивалютность:** Официальный курс НБРБ (BYN ⇄ USD) с суточным кэшированием.
* **📦 Реляционная база данных:** Полная поддержка PostgreSQL (3NF) с фолбэком на SQLite.
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================================================
# CORS МИДЛВАР (Для работы с фронтендом на любом порту и GitHub Pages)
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене можно ограничить доменом фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ПОДКЛЮЧЕНИЕ РОУТЕРОВ
# ============================================================================
app.include_router(auth.router)
app.include_router(spheres.router)
app.include_router(goals.router)
app.include_router(currency.router)
app.include_router(analytics.router)


# ============================================================================
# БАЗОВЫЕ ЭНДПОИНТЫ
# ============================================================================

@app.get(
    "/",
    include_in_schema=False,
    summary="Редирект на документацию Swagger UI"
)
def root():
    """Автоматическое перенаправление на интерактивную документацию Swagger."""
    return RedirectResponse(url="/docs")


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Проверка работоспособности сервиса (Health Check)",
    description="Возвращает статус приложения и проверяет активность подключения к базе данных."
)
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        # Проверяем выполнение простейшего SQL-запроса
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        app="Horizont Dream Map Planner API",
        version="1.0.0",
        database=db_status,
        timestamp=datetime.now(timezone.utc)
    )
