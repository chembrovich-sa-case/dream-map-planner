"""
Роутер управления целями и чек-листами декомпозиции (UC-1, UC-2, UC-5).
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import GoalCard, GoalStep, LifeSphere, User
from schemas import (
    GoalCardResponse, GoalCardDetailResponse, GoalCardCreate, GoalCardUpdate,
    GoalStepCreate, GoalStepResponse
)
from routers.auth import get_current_user

router = APIRouter(prefix="/api/goals", tags=["Goals & Dreams (Цели)"])


@router.get(
    "",
    response_model=List[GoalCardResponse],
    summary="Получить список целей пользователя с фильтрами",
    description="Возвращает витрину карточек целей с поддержкой фильтрации по сфере, статусу, приоритету и поиску."
)
def get_goals(
    sphere_id: Optional[uuid.UUID] = Query(None, description="Фильтр по сфере жизни"),
    status: Optional[str] = Query(None, description="Фильтр по статусу (draft, in_progress, achieved, archived)"),
    priority: Optional[str] = Query(None, description="Фильтр по приоритету (low, medium, high, critical)"),
    search: Optional[str] = Query(None, description="Поисковый запрос по названию или описанию"),
    user_id: Optional[uuid.UUID] = Query(None, description="Фильтр по ID пользователя"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_user_id = user_id or current_user.id
    query = db.query(GoalCard).filter(GoalCard.user_id == target_user_id)

    if sphere_id:
        query = query.filter(GoalCard.sphere_id == sphere_id)
    if status and status != "all":
        query = query.filter(GoalCard.status == status)
    if priority and priority != "all":
        query = query.filter(GoalCard.priority == priority)
    if search:
        s_term = f"%{search.strip().lower()}%"
        query = query.filter(
            (GoalCard.title.ilike(s_term)) | (GoalCard.description.ilike(s_term))
        )

    goals = query.order_by(GoalCard.created_at.desc()).all()

    result = []
    for g in goals:
        steps_count = len(g.steps)
        completed_steps_count = sum(1 for s in g.steps if s.is_completed)
        g_dict = GoalCardResponse.model_validate(g).model_dump()
        g_dict["steps_count"] = steps_count
        g_dict["completed_steps_count"] = completed_steps_count
        result.append(GoalCardResponse(**g_dict))

    return result


@router.get(
    "/{goal_id}",
    response_model=GoalCardDetailResponse,
    summary="Детальный просмотр цели со всеми шагами чек-листа (UC-5)",
    description="Возвращает полную карточку цели, привязанную сферу жизни и упорядоченный список шагов декомпозиции."
)
def get_goal_detail(
    goal_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    goal = db.query(GoalCard).options(
        joinedload(GoalCard.steps),
        joinedload(GoalCard.sphere)
    ).filter(GoalCard.id == goal_id).first()

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Цель с ID {goal_id} не найдена"
        )

    steps_count = len(goal.steps)
    completed_steps_count = sum(1 for s in goal.steps if s.is_completed)

    g_dict = GoalCardDetailResponse.model_validate(goal).model_dump()
    g_dict["steps_count"] = steps_count
    g_dict["completed_steps_count"] = completed_steps_count
    return GoalCardDetailResponse(**g_dict)


@router.post(
    "",
    response_model=GoalCardDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую цель с декомпозицией шагов",
    description="Создает цель в выбранной сфере, сохраняет шаги чек-листа и мгновенно пересчитывает балл баланса сферы."
)
def create_goal(
    goal_in: GoalCardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Проверка существования сферы
    sphere = db.query(LifeSphere).filter(LifeSphere.id == goal_in.sphere_id).first()
    if not sphere:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Сфера с ID {goal_in.sphere_id} не найдена"
        )

    new_goal = GoalCard(
        user_id=goal_in.user_id or current_user.id,
        sphere_id=goal_in.sphere_id,
        title=goal_in.title,
        description=goal_in.description,
        image_url=goal_in.image_url,
        deadline=goal_in.deadline,
        priority=goal_in.priority,
        status=goal_in.status,
        cost_amount=goal_in.cost_amount,
        currency=goal_in.currency,
        progress_percent=0
    )
    db.add(new_goal)
    db.flush()

    # Добавление переданных шагов
    if goal_in.steps:
        for idx, st in enumerate(goal_in.steps):
            step = GoalStep(
                goal_id=new_goal.id,
                title=st.title,
                is_completed=st.is_completed,
                sort_order=st.sort_order or (idx + 1),
                weight=st.weight
            )
            db.add(step)
        db.flush()

    # Пересчет прогресса цели и балла сферы
    new_goal.recalculate_progress()
    sphere.recalculate_score()

    db.commit()
    db.refresh(new_goal)

    return get_goal_detail(new_goal.id, db)


@router.put(
    "/{goal_id}",
    response_model=GoalCardDetailResponse,
    summary="Обновить данные карточки цели"
)
def update_goal(
    goal_id: uuid.UUID,
    goal_in: GoalCardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = db.query(GoalCard).filter(GoalCard.id == goal_id).first()
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Цель с ID {goal_id} не найдена"
        )

    if current_user.role != "admin" and goal.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для редактирования данной цели"
        )

    update_data = goal_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)

    goal.recalculate_progress()
    if goal.sphere:
        goal.sphere.recalculate_score()

    db.commit()
    db.refresh(goal)
    return get_goal_detail(goal.id, db)


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить карточку цели",
    description="Удаляет цель и все связанные шаги, после чего пересчитывает балл баланса соответствующей сферы."
)
def delete_goal(
    goal_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = db.query(GoalCard).filter(GoalCard.id == goal_id).first()
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Цель с ID {goal_id} не найдена"
        )

    if current_user.role != "admin" and goal.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления данной цели"
        )

    sphere = goal.sphere
    db.delete(goal)
    db.flush()

    if sphere:
        sphere.recalculate_score()

    db.commit()
    return None


# ============================================================================
# РАБОТА С ШАГАМИ ЧЕК-ЛИСТА (UC-2: ИНТЕРАКТИВНАЯ ОТМЕТКА ШАГОВ)
# ============================================================================

@router.patch(
    "/{goal_id}/steps/{step_id}/toggle",
    response_model=GoalStepResponse,
    summary="Интерактивное переключение шага чек-листа (UC-2)",
    description="Инвертирует статус is_completed, автоматически пересчитывает процент цели и текущий балл сферы в колесе баланса."
)
def toggle_goal_step(
    goal_id: uuid.UUID,
    step_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    step = db.query(GoalStep).filter(
        GoalStep.id == step_id,
        GoalStep.goal_id == goal_id
    ).first()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шаг чек-листа не найден"
        )

    # Переключаем статус
    step.toggle()

    # Мгновенно пересчитываем прогресс цели
    goal = step.goal
    goal.recalculate_progress()

    # Мгновенно пересчитываем балл сферы в радарном колесе
    if goal.sphere:
        goal.sphere.recalculate_score()

    db.commit()
    db.refresh(step)
    return GoalStepResponse.model_validate(step)


@router.post(
    "/{goal_id}/steps",
    response_model=GoalStepResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить новый шаг в чек-лист цели"
)
def add_goal_step(
    goal_id: uuid.UUID,
    step_in: GoalStepCreate,
    db: Session = Depends(get_db)
):
    goal = db.query(GoalCard).filter(GoalCard.id == goal_id).first()
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Цель с ID {goal_id} не найдена"
        )

    max_order = db.query(GoalStep.sort_order).filter(GoalStep.goal_id == goal_id).order_by(GoalStep.sort_order.desc()).first()
    next_order = (max_order[0] + 1) if max_order else 1

    new_step = GoalStep(
        goal_id=goal_id,
        title=step_in.title,
        is_completed=step_in.is_completed,
        weight=step_in.weight,
        sort_order=step_in.sort_order or next_order
    )
    db.add(new_step)
    db.flush()

    goal.recalculate_progress()
    if goal.sphere:
        goal.sphere.recalculate_score()

    db.commit()
    db.refresh(new_step)
    return GoalStepResponse.model_validate(new_step)


@router.delete(
    "/{goal_id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить шаг из чек-листа цели"
)
def delete_goal_step(
    goal_id: uuid.UUID,
    step_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    step = db.query(GoalStep).filter(
        GoalStep.id == step_id,
        GoalStep.goal_id == goal_id
    ).first()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шаг чек-листа не найден"
        )

    goal = step.goal
    db.delete(step)
    db.flush()

    goal.recalculate_progress()
    if goal.sphere:
        goal.sphere.recalculate_score()

    db.commit()
    return None
