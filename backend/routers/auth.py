"""
Роутер аутентификации и ролевого доступа (RBAC: UC-4).
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserLogin, TokenResponse, UserResponse, DemoUserItem, UserCreate

router = APIRouter(prefix="/api/auth", tags=["Authentication & RBAC"])


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Зависимость получения текущего пользователя.
    В демо-режиме: при наличии заголовка 'Authorization: Bearer <email>' или стандартного токена,
    находит соответствующего пользователя, иначе возвращает дефолтного админа.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        # Если в токене передан email (для удобства фронтенда в демо)
        if "@" in token:
            user = db.query(User).filter(User.email == token).first()
            if user:
                return user
        # Поиск по id (если токен UUID)
        try:
            user_id = uuid.UUID(token)
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user
        except ValueError:
            pass

    # По умолчанию для удобства тестирования API возвращается Администратор
    user = db.query(User).filter(User.role == "admin").first()
    if not user:
        user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден в системе"
        )
    return user


@router.get(
    "/demo-users", 
    response_model=List[DemoUserItem],
    summary="Список демонстрационных учетных записей (1-click login)",
    description="Возвращает предустановленные профили Администратора и Пользователя для быстрого переключения в UI."
)
def get_demo_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    demo_items = []
    for u in users:
        desc = "Полный доступ: управление дашбордом, справочниками сфер и CMS базой данных" if u.role == "admin" else "Пользовательский доступ: колесо баланса, витрина желаний и чек-листы"
        demo_items.append(
            DemoUserItem(
                id=u.id,
                name=u.name,
                email=u.email,
                role=u.role,
                avatar_url=u.avatar_url,
                description=desc
            )
        )
    return demo_items


@router.post(
    "/login", 
    response_model=TokenResponse,
    summary="Авторизация пользователя в системе",
    description="Проверяет email и возвращает профиль пользователя с токеном доступа (Bearer)."
)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email.lower().strip()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с адресом {credentials.email} не зарегистрирован"
        )

    # В рамках демо-версии принимаем валидный email демо-пользователей
    return TokenResponse(
        access_token=str(user.email),
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get(
    "/me", 
    response_model=UserResponse,
    summary="Получить профиль текущего пользователя",
    description="Возвращает данные пользователя, переданного в заголовке Authorization."
)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя"
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )

    new_user = User(
        email=user_in.email.lower().strip(),
        password_hash="$2a$12$demoHashPlaceHolderForSecurityMocking",
        name=user_in.name,
        role=user_in.role,
        avatar_url=user_in.avatar_url
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)
