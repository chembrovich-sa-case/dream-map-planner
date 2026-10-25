"""
Pydantic-схемы валидации входящих и исходящих данных (DTO) для FastAPI.
Обеспечивают строгую типизацию, сериализацию и автогенерацию Swagger/OpenAPI спецификации.
"""

from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional, List, Literal
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ============================================================================
# 1. ОБЩИЕ И СИСТЕМНЫЕ СХЕМЫ
# ============================================================================

class HealthResponse(BaseModel):
    status: str = Field("ok", example="ok")
    app: str = Field("Horizont Dream Map Planner API", example="Horizont Dream Map Planner API")
    version: str = Field("1.0.0", example="1.0.0")
    database: str = Field("connected", example="connected")
    timestamp: datetime


# ============================================================================
# 2. ПОЛЬЗОВАТЕЛИ И АВТОРИЗАЦИЯ (RBAC)
# ============================================================================

RoleType = Literal["admin", "user", "guest"]

class UserBase(BaseModel):
    email: str = Field(..., example="admin@horizon.app")
    username: Optional[str] = Field(None, example="admin")
    name: str = Field(..., min_length=2, max_length=100, example="Алексей Администраторов")
    role: RoleType = Field("user", example="admin")
    is_active: bool = Field(True, example=True)
    avatar_url: Optional[str] = Field(None, example="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200")


class UserCreate(UserBase):
    password: str = Field(..., min_length=4, example="SecretPass123!")


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    username: Optional[str] = Field(None, example="admin")
    email: Optional[str] = Field(None, example="admin@horizon.app")
    password: str = Field(..., example="admin")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserAdminCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, example="manager1")
    password: str = Field(..., min_length=3, max_length=100, example="Secret123")
    role: RoleType = Field("user", example="user")
    name: Optional[str] = Field(None, example="Иван Менеджеров")
    email: Optional[str] = Field(None, example="manager1@horizon.app")
    avatar_url: Optional[str] = None


class UserAdminUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[RoleType] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None


class UserAdminResponse(BaseModel):
    id: uuid.UUID
    username: Optional[str] = None
    email: str
    name: str
    role: RoleType
    is_active: bool = True
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    success: bool = True
    message: str


class DemoUserItem(BaseModel):
    id: uuid.UUID
    username: Optional[str] = None
    name: str
    email: str
    role: RoleType
    avatar_url: Optional[str]
    description: str


# ============================================================================
# 3. ШАГИ ДЕКОМПОЗИЦИИ ЦЕЛЕЙ (CHECKLIST STEPS)
# ============================================================================

class GoalStepBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, example="Пройти сертификацию TOGAF")
    weight: int = Field(1, ge=1, le=10, description="Относительная сложность/значимость шага (1-10)", example=2)
    sort_order: int = Field(0, example=1)


class GoalStepCreate(GoalStepBase):
    is_completed: bool = Field(False, example=False)


class GoalStepUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    weight: Optional[int] = Field(None, ge=1, le=10)
    sort_order: Optional[int] = None
    is_completed: Optional[bool] = None


class GoalStepResponse(GoalStepBase):
    id: uuid.UUID
    goal_id: uuid.UUID
    is_completed: bool
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 4. СФЕРЫ ЖИЗНИ (LIFE SPHERES)
# ============================================================================

class LifeSphereBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=100, example="Карьера и бизнес")
    description: Optional[str] = Field(None, example="Профессиональный рост и руководство проектами")
    color: str = Field(..., regex=r"^#[0-9A-Fa-f]{6}$", example="#3B82F6")
    icon: str = Field("compass", example="briefcase")
    target_score: Decimal = Field(Decimal("10.0"), ge=0.0, le=10.0, example=10.0)
    sort_order: int = Field(0, example=1)


class LifeSphereCreate(LifeSphereBase):
    user_id: Optional[uuid.UUID] = None


class LifeSphereUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, regex=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None
    target_score: Optional[Decimal] = Field(None, ge=0.0, le=10.0)
    sort_order: Optional[int] = None


class LifeSphereResponse(LifeSphereBase):
    id: uuid.UUID
    user_id: uuid.UUID
    current_score: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LifeSphereWithMetrics(LifeSphereResponse):
    active_goals_count: int = 0
    completed_goals_count: int = 0
    total_budget_byn: Decimal = Decimal("0.00")


# ============================================================================
# 5. КАРТОЧКИ ЦЕЛЕЙ (GOAL CARDS)
# ============================================================================

PriorityType = Literal["low", "medium", "high", "critical"]
StatusType = Literal["draft", "in_progress", "achieved", "archived"]
CurrencyType = Literal["BYN", "USD"]


class GoalCardBase(BaseModel):
    sphere_id: uuid.UUID = Field(..., example="b0000000-0000-0000-0000-000000000001")
    title: str = Field(..., min_length=2, max_length=150, example="Повышение до Lead System Architect")
    description: Optional[str] = Field(None, example="Защитить архитектурную концепцию платформы")
    image_url: Optional[str] = Field(None, example="https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=800")
    deadline: Optional[date] = Field(None, example="2026-12-01")
    priority: PriorityType = Field("medium", example="critical")
    status: StatusType = Field("in_progress", example="in_progress")
    cost_amount: Decimal = Field(Decimal("0.00"), ge=0.0, example=1200.00)
    currency: CurrencyType = Field("BYN", example="BYN")


class GoalCardCreate(GoalCardBase):
    user_id: Optional[uuid.UUID] = None
    steps: Optional[List[GoalStepCreate]] = Field(default_factory=list)


class GoalCardUpdate(BaseModel):
    sphere_id: Optional[uuid.UUID] = None
    title: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    image_url: Optional[str] = None
    deadline: Optional[date] = None
    priority: Optional[PriorityType] = None
    status: Optional[StatusType] = None
    cost_amount: Optional[Decimal] = Field(None, ge=0.0)
    currency: Optional[CurrencyType] = None


class GoalCardResponse(GoalCardBase):
    id: uuid.UUID
    user_id: uuid.UUID
    progress_percent: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    steps_count: int = 0
    completed_steps_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class GoalCardDetailResponse(GoalCardResponse):
    steps: List[GoalStepResponse] = Field(default_factory=list)
    sphere: Optional[LifeSphereResponse] = None


# ============================================================================
# 6. КУРСЫ ВАЛЮТ (EXCHANGE RATES - NBRB)
# ============================================================================

class ExchangeRateResponse(BaseModel):
    currency_code: str = "USD"
    scale: int = 1
    rate: Decimal = Decimal("2.9543")
    rate_date: date
    fetched_at: datetime
    source: str = "Официальный курс Нацбанка РБ (НБРБ)"

    model_config = ConfigDict(from_attributes=True)


class CurrencyConvertRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, example=1000.00)
    from_currency: CurrencyType = Field("USD", example="USD")
    to_currency: CurrencyType = Field("BYN", example="BYN")


class CurrencyConvertResponse(BaseModel):
    amount: Decimal
    from_currency: CurrencyType
    to_currency: CurrencyType
    rate: Decimal
    converted_amount: Decimal
    rate_date: date


# ============================================================================
# 7. СРЕЗЫ БАЛАНСА И АНАЛИТИКА (BALANCE SNAPSHOTS & TRENDS)
# ============================================================================

class BalanceSnapshotItemBase(BaseModel):
    sphere_id: uuid.UUID
    score: Decimal = Field(..., ge=0.0, le=10.0, example=7.5)
    target_score: Decimal = Field(Decimal("10.0"), ge=0.0, le=10.0, example=10.0)


class BalanceSnapshotItemCreate(BalanceSnapshotItemBase):
    pass


class BalanceSnapshotItemResponse(BalanceSnapshotItemBase):
    id: uuid.UUID
    snapshot_id: uuid.UUID
    sphere_title: Optional[str] = None
    sphere_color: Optional[str] = None
    sphere_icon: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BalanceSnapshotCreate(BaseModel):
    notes: Optional[str] = Field(None, example="Регулярный срез колеса баланса")
    recorded_at: Optional[datetime] = None
    items: Optional[List[BalanceSnapshotItemCreate]] = None


class BalanceSnapshotResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    overall_harmony_index: Optional[Decimal] = None
    notes: Optional[str] = None
    scores_data: Optional[dict] = None
    recorded_at: datetime
    created_at: datetime
    items: List[BalanceSnapshotItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AnalyticsSphereSeries(BaseModel):
    sphere_id: uuid.UUID
    title: str
    color: str
    icon: str
    scores: List[float]


class AnalyticsTrendResponse(BaseModel):
    labels: List[str]
    dates: List[str]
    harmony_series: List[float]
    spheres_series: List[AnalyticsSphereSeries]
    snapshots_count: int
    current_harmony_index: float
    earliest_harmony_index: float
    improvement_delta: float
    improvement_percent: float
