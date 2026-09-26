"""
Authentication Routes
=====================
Provides API endpoints for user sign-in, session status verification, and logout.
Utilizes HTTP-only cookies to securely persist signed JWT sessions without
exposing tokens to client-side scripts.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Response, HTTPException, status, Depends
from services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user,
    COOKIE_NAME,
    REMEMBER_ME_DAYS,
    DEFAULT_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: Optional[bool] = False


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str


class LoginResponse(BaseModel):
    success: bool
    user: UserResponse


class MeResponse(BaseModel):
    authenticated: bool
    user: UserResponse


class LogoutResponse(BaseModel):
    success: bool
    message: str


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, response: Response):
    """
    Authenticates operator with email and password.
    Sets signed JWT in secure HTTP-only cookie.
    """
    user = authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Compute cookie max-age
    if credentials.remember_me:
        max_age = REMEMBER_ME_DAYS * 24 * 3600
    else:
        max_age = DEFAULT_EXPIRE_MINUTES * 60

    token = create_access_token(user, remember_me=bool(credentials.remember_me))

    # Set secure HTTP-only cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=max_age,
        path="/",
        httponly=True,
        samesite="lax",
        secure=False  # allow localhost development
    )

    return LoginResponse(
        success=True,
        user=UserResponse(
            id=user["user_id"],
            email=user["email"],
            name=user["name"],
            role=user["role"]
        )
    )


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Validates current authenticated operator session from HTTP-only cookie.
    Returns operator profile information.
    """
    return MeResponse(
        authenticated=True,
        user=UserResponse(
            id=current_user["user_id"],
            email=current_user["email"],
            name=current_user["name"],
            role=current_user["role"]
        )
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response):
    """
    Terminates operator session by clearing the HTTP-only cookie.
    """
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax"
    )
    return LogoutResponse(
        success=True,
        message="Logged out successfully."
    )
