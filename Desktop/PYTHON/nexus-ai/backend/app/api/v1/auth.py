import uuid as _uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.limiter import limiter
from app.db.postgres import get_db
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserOut, Token
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
@limiter.limit("5/minute")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=Role.viewer,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    return Token(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id), user.role.value),
    )


@router.post("/refresh", response_model=Token)
def refresh(refresh_token: str):
    data = decode_token(refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    return Token(
        access_token=create_access_token(data["sub"], data["role"]),
        refresh_token=create_refresh_token(data["sub"], data["role"]),
    )


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), user_data=Depends(get_current_user)):
    user = db.query(User).filter(User.id == _uuid.UUID(user_data["user_id"])).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user
