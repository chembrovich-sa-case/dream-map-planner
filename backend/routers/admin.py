"""
Роутер ручного управления пользователями (User Provisioning / Admin Panel).
Все эндпоинты защищены зависимостью require_admin и доступны СТРОГО роли 'admin'.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import (
    UserAdminResponse, 
    UserAdminCreate, 
    UserAdminUpdate, 
    MessageResponse
)
from routers.auth import require_admin
from security import get_password_hash

router = APIRouter(prefix="/api/admin", tags=["Admin & User Provisioning (Ручной Provisioning)"])


@router.get(
    "/users",
    response_model=List[UserAdminResponse],
    summary="Реестр всех пользователей закрытого контура (Admin Only)",
    description="Возвращает список всех созданных пользователей с их ролями и статусом активности. Доступно только администраторам."
)
def list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    users = db.query(User).order_by(User.created_at.asc()).all()
    return [UserAdminResponse.model_validate(u) for u in users]


@router.post(
    "/users",
    response_model=UserAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ручное создание пользователя администратором (Admin Provisioning)",
    description="Администратор вручную регистрирует резидента, задавая логин, начальный пароль, имя и роль ('admin' или 'user')."
)
def create_user(
    user_in: UserAdminCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    clean_username = user_in.username.strip().lower()
    
    # Нормализация email: если не указан явно, генерируем {username}@horizon.app
    clean_email = (user_in.email or f"{clean_username}@horizon.app").strip().lower()
    clean_name = (user_in.name or user_in.username).strip()
    clean_role = user_in.role.strip().lower()
    
    if clean_role not in ("admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Роль должна быть 'admin' или 'user'"
        )

    # Проверка уникальности логина и email
    existing_user = db.query(User).filter(
        (User.username == clean_username) | (User.email == clean_email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Пользователь с логином «{clean_username}» или email «{clean_email}» уже существует"
        )

    # Хэширование пароля
    password_hash = get_password_hash(user_in.password)

    new_user = User(
        id=uuid.uuid4(),
        username=clean_username,
        email=clean_email,
        password_hash=password_hash,
        name=clean_name,
        role=clean_role,
        is_active=True,
        avatar_url=user_in.avatar_url or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserAdminResponse.model_validate(new_user)


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Удаление или блокировка пользователя (Admin Only)",
    description="Удаляет учетную запись пользователя или деактивирует (is_active=False). Нельзя заблокировать или удалить собственный аккаунт администратора."
)
def delete_or_deactivate_user(
    user_id: uuid.UUID,
    deactivate_only: bool = Query(False, description="Если True, только блокирует (is_active=False) без физического удаления"),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {user_id} не найден"
        )

    if target.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя заблокировать или удалить собственный аккаунт администратора"
        )

    if deactivate_only:
        target.is_active = False
        db.commit()
        return MessageResponse(
            success=True,
            message=f"Пользователь «{target.name}» ({target.username or target.email}) успешно заблокирован"
        )

    db.delete(target)
    db.commit()
    return MessageResponse(
        success=True,
        message=f"Пользователь «{target.name}» ({target.username or target.email}) успешно удален из системы"
    )
