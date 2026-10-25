"""
Модуль подключения к базе данных PostgreSQL через SQLAlchemy.
Синхронизирован со схемой database/schema.sql проекта «Горизонт».
"""

import os
import uuid
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Строка подключения: берется из переменной окружения DATABASE_URL или используется дефолт для PostgreSQL
# Для локальной разработки без запущенного PostgreSQL можно указать sqlite:///./horizont.db
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg2://postgres:postgres@localhost:5432/horizont_db"
)

# Настройка аргументов соединения
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=os.getenv("SQL_ECHO", "False").lower() in ("true", "1")
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Генератор сессии БД (FastAPI Dependency).
    Гарантирует автоматическое закрытие сессии после завершения HTTP-запроса.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Создание всех таблиц в базе данных и наполнение демо-данными при первом запуске.
    """
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    
    with SessionLocal() as db:
        seed_initial_data(db)


def seed_initial_data(db: Session):
    """
    Наполнение БД начальными демо-данными из схемы schema.sql, если таблицы пусты.
    """
    from models import User, LifeSphere, GoalCard, GoalStep, ExchangeRateCache
    from datetime import date

    # 1. Проверяем наличие пользователей
    if db.query(User).first() is not None:
        return

    print("🌱 Инициализация демонстрационных данных в базе данных Горизонт...")

    # 2. Создаем демо-пользователей (admin и user)
    admin_id = uuid.UUID("a0000000-0000-0000-0000-000000000000")
    user_id = uuid.UUID("a0000000-0000-0000-0000-000000000001")

    admin = User(
        id=admin_id,
        email="admin@horizon.app",
        password_hash="$2a$12$e8Y5t1R1CgG6n3G9C9a1qOYQ7qf/v6YkP7fWbL2q7dFpP5Z8vK9G6",
        name="Алексей Администраторов",
        role="admin",
        avatar_url="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=300&q=80"
    )

    regular_user = User(
        id=user_id,
        email="user@horizon.app",
        password_hash="$2a$12$e8Y5t1R1CgG6n3G9C9a1qOYQ7qf/v6YkP7fWbL2q7dFpP5Z8vK9G6",
        name="Иван Горизонтов",
        role="user",
        avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80"
    )

    db.add_all([admin, regular_user])
    db.flush()

    # 3. Создаем 6 сфер колеса баланса (для обоих пользователей)
    spheres_data = [
        {
            "id": uuid.UUID("b0000000-0000-0000-0000-000000000001"),
            "title": "Карьера и бизнес",
            "description": "Профессиональный рост, руководящие роли, масштабные рабочие проекты",
            "color": "#3B82F6",
            "icon": "briefcase",
            "target_score": 10.0,
            "current_score": 6.7,
            "sort_order": 1
        },
        {
            "id": uuid.UUID("b0000000-0000-0000-0000-000000000002"),
            "title": "Финансы и капитал",
            "description": "Личный бюджет, финансовая подушка безопасности и инвестиционный портфель",
            "color": "#10B981",
            "icon": "wallet",
            "target_score": 10.0,
            "current_score": 7.5,
            "sort_order": 2
        },
        {
            "id": uuid.UUID("b0000000-0000-0000-0000-000000000003"),
            "title": "Здоровье и спорт",
            "description": "Физическая форма, бег, сон, правильное питание и регулярные чекапы",
            "color": "#EF4444",
            "icon": "heart-pulse",
            "target_score": 10.0,
            "current_score": 5.0,
            "sort_order": 3
        },
        {
            "id": uuid.UUID("b0000000-0000-0000-0000-000000000004"),
            "title": "Семья и отношения",
            "description": "Качественное время с близкими, романтические свидания и семейные традиции",
            "color": "#EC4899",
            "icon": "users",
            "target_score": 10.0,
            "current_score": 8.0,
            "sort_order": 4
        },
        {
            "id": uuid.UUID("b0000000-0000-0000-0000-000000000005"),
            "title": "Саморазвитие и навыки",
            "description": "Чтение профильной литературы, изучение языков, курсы и менторство",
            "color": "#8B5CF6",
            "icon": "book-open",
            "target_score": 10.0,
            "current_score": 6.0,
            "sort_order": 5
        },
        {
            "id": uuid.UUID("b0000000-0000-0000-0000-000000000006"),
            "title": "Яркость жизни и хобби",
            "description": "Путешествия, новые впечатления, фотография и творческий отдых",
            "color": "#F59E0B",
            "icon": "compass",
            "target_score": 10.0,
            "current_score": 4.5,
            "sort_order": 6
        }
    ]

    spheres_objs = []
    for s in spheres_data:
        sphere = LifeSphere(
            id=s["id"],
            user_id=admin_id,
            title=s["title"],
            description=s["description"],
            color=s["color"],
            icon=s["icon"],
            target_score=s["target_score"],
            current_score=s["current_score"],
            sort_order=s["sort_order"]
        )
        spheres_objs.append(sphere)
    
    db.add_all(spheres_objs)
    db.flush()

    # 4. Создаем демонстрационные цели с шагами чек-листа
    goals_data = [
        {
            "id": uuid.UUID("c0000000-0000-0000-0000-000000000001"),
            "sphere_id": uuid.UUID("b0000000-0000-0000-0000-000000000001"),
            "title": "Повышение до Lead System Architect",
            "description": "Защитить архитектурную концепцию микросервисной платформы и возглавить стрим архитектуры",
            "image_url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=800&q=80",
            "deadline": date(2026, 12, 1),
            "priority": "critical",
            "status": "in_progress",
            "progress_percent": 67,
            "cost_amount": 1200.00,
            "currency": "BYN",
            "steps": [
                ("Пройти сертификацию TOGAF / AWS Solutions Architect", True, 2),
                ("Разработать и защитить архитектурный манифест проекта", True, 2),
                ("Провести 3 публичных воркшопа для аналитиков команды", False, 1)
            ]
        },
        {
            "id": uuid.UUID("c0000000-0000-0000-0000-000000000002"),
            "sphere_id": uuid.UUID("b0000000-0000-0000-0000-000000000002"),
            "title": "Сформировать капитал подушки $10,000",
            "description": "Накопить неприкосновенный резервный фонд в надежных активах на 6 месяцев жизни",
            "image_url": "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?auto=format&fit=crop&w=800&q=80",
            "deadline": date(2027, 3, 1),
            "priority": "high",
            "status": "in_progress",
            "progress_percent": 75,
            "cost_amount": 10000.00,
            "currency": "USD",
            "steps": [
                ("Открыть отдельный накопительный вклад", True, 1),
                ("Достичь отметки в $5,000", True, 2),
                ("Достичь целевой отметки в $10,000", False, 2)
            ]
        },
        {
            "id": uuid.UUID("c0000000-0000-0000-0000-000000000003"),
            "sphere_id": uuid.UUID("b0000000-0000-0000-0000-000000000003"),
            "title": "Пробежать Минский полумарафон (21.1 км)",
            "description": "Подготовиться по плану тренера, снизить пульсовую стоимость бега и финишировать без травм",
            "image_url": "https://images.unsplash.com/photo-1452626038306-9aae5e071dd3?auto=format&fit=crop&w=800&q=80",
            "deadline": date(2026, 9, 15),
            "priority": "high",
            "status": "in_progress",
            "progress_percent": 50,
            "cost_amount": 450.00,
            "currency": "BYN",
            "steps": [
                ("Пройти кардио-чекап у спортивного врача", True, 1),
                ("Подобрать профессиональные кроссовки с поддержкой", True, 1),
                ("Пробежать длительную тренировку 16 км", False, 2),
                ("Успешный финиш на полумарафоне в Минске", False, 2)
            ]
        },
        {
            "id": uuid.UUID("c0000000-0000-0000-0000-000000000006"),
            "sphere_id": uuid.UUID("b0000000-0000-0000-0000-000000000006"),
            "title": "Путешествие в Норвежские фьорды",
            "description": "Арендовать кемпер и проехать живописный маршрут по Атлантической дороге",
            "image_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
            "deadline": date(2027, 7, 20),
            "priority": "medium",
            "status": "in_progress",
            "progress_percent": 33,
            "cost_amount": 2800.00,
            "currency": "USD",
            "steps": [
                ("Составить трек маршрута и точки стоянок", True, 1),
                ("Забронировать кемпер и билеты", False, 2),
                ("Отправиться в путешествие", False, 3)
            ]
        }
    ]

    for g_info in goals_data:
        goal = GoalCard(
            id=g_info["id"],
            user_id=admin_id,
            sphere_id=g_info["sphere_id"],
            title=g_info["title"],
            description=g_info["description"],
            image_url=g_info["image_url"],
            deadline=g_info["deadline"],
            priority=g_info["priority"],
            status=g_info["status"],
            progress_percent=g_info["progress_percent"],
            cost_amount=g_info["cost_amount"],
            currency=g_info["currency"]
        )
        db.add(goal)
        db.flush()

        for idx, (st_title, is_comp, weight) in enumerate(g_info["steps"]):
            step = GoalStep(
                goal_id=goal.id,
                title=st_title,
                is_completed=is_comp,
                sort_order=idx + 1,
                weight=weight
            )
            db.add(step)

    # 5. Кэш курса валюты НБРБ
    fx = ExchangeRateCache(
        currency_code="USD",
        scale=1,
        rate=2.9543,
        rate_date=date.today()
    )
    db.merge(fx)

    db.commit()
    print("✅ База данных успешно инициализирована демо-данными!")
