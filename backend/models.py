"""
ORM-модели базы данных проекта «Горизонт» (SQLAlchemy 2.0).
Полностью соответствуют 3NF схеме database/schema.sql.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Numeric, Date, 
    DateTime, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import relationship
from database import Base


class GUID(TypeDecorator):
    """
    Платформонезависимый тип UUID.
    В PostgreSQL использует нативный тип UUID, в SQLite - CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value


class User(Base):
    """
    Учетные записи пользователей сервиса с ролевой моделью (RBAC).
    """
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # 'admin', 'user', 'guest'
    avatar_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user', 'guest')", name="chk_users_role"),
    )

    # Связи
    spheres = relationship("LifeSphere", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("GoalCard", back_populates="user", cascade="all, delete-orphan")
    snapshots = relationship("BalanceSnapshot", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class LifeSphere(Base):
    """
    Сферы жизни пользователя для радарной диаграммы баланса.
    """
    __tablename__ = "life_spheres"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=False)  # Hex формат: #3B82F6
    icon = Column(String(50), nullable=False)   # Имя Lucide иконки
    target_score = Column(Numeric(3, 1), nullable=False, default=10.0)
    current_score = Column(Numeric(3, 1), nullable=False, default=0.0)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("target_score >= 0.0 AND target_score <= 10.0", name="chk_life_spheres_target_score"),
        CheckConstraint("current_score >= 0.0 AND current_score <= 10.0", name="chk_life_spheres_current_score"),
    )

    # Связи
    user = relationship("User", back_populates="spheres")
    goals = relationship("GoalCard", back_populates="sphere", cascade="all, delete-orphan")

    def recalculate_score(self):
        """
        Пересчет текущего балла сферы на основе взвешенного прогресса активных целей.
        Соответствует представлению v_sphere_radar_metrics.
        """
        active_goals = [g for g in self.goals if g.status != "archived"]
        if not active_goals:
            self.current_score = 0.0
            return 0.0

        total_weight = 0
        total_weighted_progress = 0.0

        priority_weights = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4
        }

        for goal in active_goals:
            weight = priority_weights.get(goal.priority, 2)
            total_weight += weight
            total_weighted_progress += (float(goal.progress_percent) / 100.0) * weight

        if total_weight > 0:
            new_score = round((total_weighted_progress / total_weight) * 10.0, 1)
            self.current_score = min(10.0, max(0.0, new_score))
        else:
            self.current_score = 0.0

        return float(self.current_score)

    def __repr__(self):
        return f"<LifeSphere '{self.title}' ({self.current_score}/{self.target_score})>"


class GoalCard(Base):
    """
    Карточки целей и желаний с привязкой к сферам жизни и декомпозицией шагов.
    """
    __tablename__ = "goal_cards"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sphere_id = Column(GUID, ForeignKey("life_spheres.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    deadline = Column(Date, nullable=True)
    priority = Column(String(20), nullable=False, default="medium")  # 'low', 'medium', 'high', 'critical'
    status = Column(String(20), nullable=False, default="in_progress")  # 'draft', 'in_progress', 'achieved', 'archived'
    progress_percent = Column(Integer, nullable=False, default=0)
    cost_amount = Column(Numeric(12, 2), nullable=False, default=0.00)
    currency = Column(String(3), nullable=False, default="BYN")  # 'BYN', 'USD'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high', 'critical')", name="chk_goal_cards_priority"),
        CheckConstraint("status IN ('draft', 'in_progress', 'achieved', 'archived')", name="chk_goal_cards_status"),
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="chk_goal_cards_progress"),
        CheckConstraint("currency IN ('BYN', 'USD')", name="chk_goal_cards_currency"),
        CheckConstraint("cost_amount >= 0.00", name="chk_goal_cards_cost"),
    )

    # Связи
    user = relationship("User", back_populates="goals")
    sphere = relationship("LifeSphere", back_populates="goals")
    steps = relationship("GoalStep", back_populates="goal", cascade="all, delete-orphan", order_by="GoalStep.sort_order")

    def recalculate_progress(self):
        """
        Динамический пересчет прогресса цели на основе взвешенных шагов чек-листа.
        Соответствует представлению v_goal_progress.
        """
        if not self.steps:
            self.progress_percent = 100 if self.status == "achieved" else 0
            return self.progress_percent

        total_weight = sum(s.weight for s in self.steps)
        completed_weight = sum(s.weight for s in self.steps if s.is_completed)

        if total_weight > 0:
            calc_percent = int(round((completed_weight / total_weight) * 100))
            self.progress_percent = min(100, max(0, calc_percent))
        else:
            self.progress_percent = 0

        # Автоматический перевод статуса при 100% выполнении
        if self.progress_percent == 100 and self.status == "in_progress":
            self.status = "achieved"
            self.completed_at = datetime.now(timezone.utc)
        elif self.progress_percent < 100 and self.status == "achieved":
            self.status = "in_progress"
            self.completed_at = None

        return self.progress_percent

    def __repr__(self):
        return f"<GoalCard '{self.title}' [{self.status}] ({self.progress_percent}%)>"


class GoalStep(Base):
    """
    Атомарные шаги декомпозиции цели в чек-листе.
    """
    __tablename__ = "goal_steps"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    goal_id = Column(GUID, ForeignKey("goal_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    is_completed = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    weight = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("weight > 0", name="chk_goal_steps_weight"),
    )

    # Связи
    goal = relationship("GoalCard", back_populates="steps")

    def toggle(self):
        """
        Переключение флага выполнения шага.
        """
        self.is_completed = not self.is_completed
        self.completed_at = datetime.now(timezone.utc) if self.is_completed else None
        return self.is_completed

    def __repr__(self):
        return f"<GoalStep '{self.title}' [{'x' if self.is_completed else ' '}]>"


class BalanceSnapshot(Base):
    """
    Исторические точки фиксации баланса жизни (срезы радарного колеса).
    """
    __tablename__ = "balance_snapshots"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_harmony_index = Column(Numeric(3, 2), nullable=True)
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("overall_harmony_index >= 0.00 AND overall_harmony_index <= 1.00", name="chk_balance_snapshots_harmony"),
    )

    # Связи
    user = relationship("User", back_populates="snapshots")
    items = relationship("BalanceSnapshotItem", back_populates="snapshot", cascade="all, delete-orphan")


class BalanceSnapshotItem(Base):
    """
    Показатели отдельных сфер в рамках исторического замера.
    """
    __tablename__ = "balance_snapshot_items"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(GUID, ForeignKey("balance_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    sphere_id = Column(GUID, ForeignKey("life_spheres.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Numeric(3, 1), nullable=False)
    target_score = Column(Numeric(3, 1), nullable=False, default=10.0)

    __table_args__ = (
        UniqueConstraint("snapshot_id", "sphere_id", name="uq_snapshot_sphere"),
        CheckConstraint("score >= 0.0 AND score <= 10.0", name="chk_snapshot_items_score"),
        CheckConstraint("target_score >= 0.0 AND target_score <= 10.0", name="chk_snapshot_items_target"),
    )

    # Связи
    snapshot = relationship("BalanceSnapshot", back_populates="items")
    sphere = relationship("LifeSphere")


class ExchangeRateCache(Base):
    """
    Суточный кэш официальных курсов валют Нацбанка РБ (НБРБ).
    """
    __tablename__ = "exchange_rates_cache"

    currency_code = Column(String(3), primary_key=True)  # 'USD', 'EUR', 'RUB', 'CNY', 'BYN'
    scale = Column(Integer, nullable=False, default=1)
    rate = Column(Numeric(10, 4), nullable=False)
    rate_date = Column(Date, nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<ExchangeRateCache {self.currency_code} = {self.rate} BYN on {self.rate_date}>"
