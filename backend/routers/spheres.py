"""
Роутер управления сферами жизни (Колесо баланса).
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from database import get_db
from models import LifeSphere, User
from schemas import (
    LifeSphereResponse, LifeSphereCreate, LifeSphereUpdate, LifeSphereWithMetrics
)
from routers.auth import get_current_user

router = APIRouter(prefix="/api/spheres", tags=["Life Spheres (Баланс)"])


@router.get(
    "",
    response_model=List[LifeSphereResponse],
    summary="Получить список сфер жизни пользователя",
    description="Возвращает упорядоченный список сфер для построения радарного колеса баланса и фильтрации целей."
)
def get_spheres(
    user_id: Optional[uuid.UUID] = Query(None, description="Фильтр по ID пользователя (по умолчанию текущий пользователь)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_user_id = user_id or current_user.id
    spheres = db.query(LifeSphere).filter(LifeSphere.user_id == target_user_id).order_by(LifeSphere.sort_order.asc()).all()
    
    # Автоматический пересчет баллов для актуальности радарной диаграммы
    for s in spheres:
        s.recalculate_score()
    db.commit()

    return [LifeSphereResponse.model_validate(s) for s in spheres]


@router.get(
    "/{sphere_id}",
    response_model=LifeSphereWithMetrics,
    summary="Получить сферу по ID с расширенными метриками"
)
def get_sphere(
    sphere_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    sphere = db.query(LifeSphere).filter(LifeSphere.id == sphere_id).first()
    if not sphere:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Сфера с ID {sphere_id} не найдена"
        )
    
    sphere.recalculate_score()
    db.commit()

    active_goals = [g for g in sphere.goals if g.status != "archived"]
    completed_goals = [g for g in sphere.goals if g.status == "achieved"]

    # Суммарный бюджет целей в BYN (с учетом фикс-курса 2.9543 при USD)
    total_budget_byn = sum(
        float(g.cost_amount) * (2.9543 if g.currency == "USD" else 1.0)
        for g in active_goals
    )

    resp_dict = LifeSphereResponse.model_validate(sphere).model_dump()
    resp_dict.update({
        "active_goals_count": len(active_goals),
        "completed_goals_count": len(completed_goals),
        "total_budget_byn": round(total_budget_byn, 2)
    })
    return LifeSphereWithMetrics(**resp_dict)


@router.post(
    "",
    response_model=LifeSphereResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую сферу жизни",
    description="Доступно Администраторам для управления справочником сфер через CMS (UC-3)."
)
def create_sphere(
    sphere_in: LifeSphereCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RBAC проверка: добавлять сферы могут только администраторы
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Создание сфер доступно только администраторам системы"
        )

    # Определяем следующий порядковый номер
    max_order = db.query(LifeSphere.sort_order).filter(LifeSphere.user_id == current_user.id).order_by(LifeSphere.sort_order.desc()).first()
    next_order = (max_order[0] + 1) if max_order else 1

    new_sphere = LifeSphere(
        user_id=sphere_in.user_id or current_user.id,
        title=sphere_in.title,
        description=sphere_in.description,
        color=sphere_in.color,
        icon=sphere_in.icon or "compass",
        target_score=sphere_in.target_score,
        current_score=0.0,
        sort_order=sphere_in.sort_order or next_order
    )
    db.add(new_sphere)
    db.commit()
    db.refresh(new_sphere)
    return LifeSphereResponse.model_validate(new_sphere)


@router.put(
    "/{sphere_id}",
    response_model=LifeSphereResponse,
    summary="Обновить сферу жизни"
)
def update_sphere(
    sphere_id: uuid.UUID,
    sphere_in: LifeSphereUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sphere = db.query(LifeSphere).filter(LifeSphere.id == sphere_id).first()
    if not sphere:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Сфера с ID {sphere_id} не найдена"
        )

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Редактирование справочника сфер доступно только администраторам системы"
        )

    update_data = sphere_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sphere, field, value)

    sphere.recalculate_score()
    db.commit()
    db.refresh(sphere)
    return LifeSphereResponse.model_validate(sphere)


@router.delete(
    "/{sphere_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить сферу жизни",
    description="Удаляет сферу и каскадно все связанные карточки целей."
)
def delete_sphere(
    sphere_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sphere = db.query(LifeSphere).filter(LifeSphere.id == sphere_id).first()
    if not sphere:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Сфера с ID {sphere_id} не найдена"
        )

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Удаление сфер доступно только администраторам системы"
        )

    db.delete(sphere)
    db.commit()
    return None
