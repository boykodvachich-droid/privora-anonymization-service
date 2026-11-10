from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError

from app import database
from app.models import User
from app.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise unauthorized

    user_id = payload["sub"]
    db = database.SessionLocal()

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if user is None:
            raise unauthorized

        return user.id
    finally:
        db.close()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest):
    db = database.SessionLocal()

    try:
        existing_user = (
            db.query(User)
            .filter(User.email == payload.email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            created_at=datetime.now(timezone.utc),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    finally:
        db.close()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    db = database.SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.email == payload.email)
            .first()
        )

        if user is None or not verify_password(
            payload.password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(user.id)

        return TokenResponse(
            access_token=token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    finally:
        db.close()


@router.get("/me", response_model=UserResponse)
def get_me(user_id: str = Depends(get_current_user_id)):
    db = database.SessionLocal()

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return user
    finally:
        db.close()
