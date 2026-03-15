from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_user_by_email,
    hash_password,
    verify_password, get_current_user,
)
from app.core.utils import generate_uuid
from app.models.user import User, UserRole
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_user(
        user: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    existing = await get_user_by_email(user.email, db)

    if existing:
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    new_user = User(
        id=generate_uuid(),
        email=user.email,
        password=hash_password(user.password),
        role=user.role
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.get("/users/search")
async def search_users(
        email: str,
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.manager:
        raise HTTPException(status_code=403, detail="Only managers can search users")

    result = await db.execute(select(User).where(User.email.ilike(f"%{email}%")))
    users = result.scalars().all()
    return [{"id": u.id, "email": u.email} for u in users]


@router.post("/login", response_model=Token)
async def login_user(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(form_data.username, db)

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    access_token = create_access_token(
        {"sub": user.email},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id
    )