"""Registration and login endpoints."""
import os
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email = str(payload.email).strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    try:
        encoded = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    user = User(name=payload.name.strip(), email=email, password_hash=encoded)
    db.add(user)
    db.commit()
    db.refresh(user)
    from app.auth import ACCESS_TOKEN_MINUTES
    access_token = create_access_token(user)
    response.set_cookie(
        key="autoclip_access_token", value=access_token, httponly=True,
        secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        samesite="strict", max_age=ACCESS_TOKEN_MINUTES * 60, path="/",
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_MINUTES * 60,
        user=UserResponse(id=user.id, name=user.name, email=user.email),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    email = str(payload.email).strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    from app.auth import ACCESS_TOKEN_MINUTES
    return TokenResponse(
        access_token=create_access_token(user),
        expires_in=ACCESS_TOKEN_MINUTES * 60,
        user=UserResponse(id=user.id, name=user.name, email=user.email),
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, name=user.name, email=user.email)
