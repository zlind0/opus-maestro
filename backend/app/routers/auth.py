from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.schemas import Token, UserOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "detail": "Incorrect username or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(
        access_token=access_token,
        user=UserOut(username=user.username, role=user.role),
    )


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return UserOut(username=user.username, role=user.role)


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Register a new user. First user becomes admin."""
    result = await db.execute(select(User).where(User.username == form_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST_PARAMS", "detail": "Username already exists"})

    # First user is admin
    count_result = await db.execute(select(User))
    is_first = count_result.first() is None

    user = User(
        username=form_data.username,
        hashed_password=hash_password(form_data.password),
        role="admin" if is_first else "user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut(username=user.username, role=user.role)
