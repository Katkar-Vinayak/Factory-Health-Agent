"""
Authentication Service
======================
Handles user credential verification, password hashing, JWT generation/validation,
and FastAPI dependencies for user session management.
Uses CSV storage for compatibility with the existing factory dataset architecture.
"""

import os
import csv
import re
import datetime
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
USERS_CSV = os.path.join(DATA_DIR, "users.csv")

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "factory-health-agent-jwt-secret-key-2026-production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
DEFAULT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours
REMEMBER_ME_DAYS = 7

COOKIE_NAME = "access_token"

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Optional Bearer for API clients that send Authorization headers
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with a secure salt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def ensure_users_csv_exists(data_dir: Optional[str] = None) -> str:
    """
    Ensures users.csv exists with correct header.
    If missing, seeds the initial provisioned demo operator account.
    """
    target_dir = data_dir or DATA_DIR
    target_file = os.path.join(target_dir, "users.csv")

    header = ["user_id", "email", "name", "role", "password_hash", "active", "created_at"]

    if not os.path.exists(target_file) or os.path.getsize(target_file) == 0:
        os.makedirs(target_dir, exist_ok=True)
        demo_password = os.environ.get("DEMO_OPERATOR_PASSWORD", "Factory@123!")
        demo_hash = hash_password(demo_password)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with open(target_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerow([
                "USR-001",
                "operator@factory.com",
                "Factory Operator",
                "operator",
                demo_hash,
                "true",
                now_iso
            ])
    return target_file


def get_all_users(data_dir: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Loads all users keyed by email."""
    target_file = ensure_users_csv_exists(data_dir)
    users = {}
    if not os.path.exists(target_file):
        return users

    with open(target_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = (row.get("email") or "").strip().lower()
            if email:
                users[email] = {
                    "user_id": row.get("user_id"),
                    "email": email,
                    "name": row.get("name"),
                    "role": row.get("role", "operator"),
                    "password_hash": row.get("password_hash"),
                    "active": (row.get("active") or "").strip().lower() in ["true", "1", "yes"],
                    "created_at": row.get("created_at")
                }
    return users


def get_user_by_email(email: str, data_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Finds user by email (case-insensitive)."""
    users = get_all_users(data_dir)
    return users.get(email.strip().lower())


def get_user_by_id(user_id: str, data_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Finds user by user_id."""
    users = get_all_users(data_dir)
    for u in users.values():
        if u.get("user_id") == user_id:
            return u
    return None


def authenticate_user(email: str, password: str, data_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Validates user credentials against password hash.
    Returns user dict without password_hash if valid, else None.
    """
    if not email or not password or not EMAIL_REGEX.match(email.strip()):
        return None

    user = get_user_by_email(email, data_dir)
    if not user:
        return None

    if not user.get("active"):
        return None

    if not verify_password(password, user.get("password_hash", "")):
        return None

    # Return safe user dictionary
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "active": user["active"],
        "created_at": user["created_at"]
    }


def create_access_token(
    user: Dict[str, Any],
    remember_me: bool = False,
    secret_key: Optional[str] = None
) -> str:
    """Generates a signed JWT with expiration timestamp."""
    secret = secret_key or JWT_SECRET_KEY
    now = datetime.datetime.now(datetime.timezone.utc)

    if remember_me:
        expire = now + datetime.timedelta(days=REMEMBER_ME_DAYS)
    else:
        expire = now + datetime.timedelta(minutes=DEFAULT_EXPIRE_MINUTES)

    payload = {
        "sub": user["user_id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "role": user.get("role", "operator"),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }

    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, secret_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Decodes and verifies a JWT token.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    secret = secret_key or JWT_SECRET_KEY
    return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])


def extract_token(request: Request, bearer_auth: Optional[HTTPAuthorizationCredentials] = None) -> Optional[str]:
    """Extracts JWT token from HTTP-only cookie first, then Authorization Bearer header."""
    # 1. Primary: HTTP-only cookie
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token

    # 2. Secondary: Authorization Bearer header
    if bearer_auth and bearer_auth.credentials:
        return bearer_auth.credentials

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


async def get_current_user(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency for protecting routes.
    Extracts token, verifies signature and expiration, verifies active user account.
    Raises HTTP 401 if unauthenticated.
    """
    token = extract_token(request, bearer)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = get_user_by_id(user_id)
    if not user or not user.get("active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or no longer exists.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "active": user["active"]
    }


async def get_optional_current_user(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[Dict[str, Any]]:
    """Retrieves current user if authenticated, else returns None without raising 401."""
    try:
        return await get_current_user(request, bearer)
    except HTTPException:
        return None
