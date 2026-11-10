import base64
import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "RS256")
JWT_ISSUER = "privora-api"
JWT_AUDIENCE = "privora-client"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)


def _load_key(variable: str) -> bytes:
    value = os.getenv(variable)

    if not value:
        raise RuntimeError(f"{variable} is not configured")

    try:
        return base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise RuntimeError(f"{variable} is not valid Base64") from exc


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: str) -> str:
    if JWT_ALGORITHM != "RS256":
        raise RuntimeError("Only RS256 is supported")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "type": "access",
    }

    return jwt.encode(
        payload,
        _load_key("JWT_PRIVATE_KEY_B64"),
        algorithm="RS256",
    )


def decode_access_token(token: str) -> dict:
    if JWT_ALGORITHM != "RS256":
        raise RuntimeError("Only RS256 is supported")

    payload = jwt.decode(
        token,
        _load_key("JWT_PUBLIC_KEY_B64"),
        algorithms=["RS256"],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={
            "require": ["sub", "iat", "exp", "iss", "aud"],
        },
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")

    if not isinstance(payload.get("sub"), str) or not payload["sub"]:
        raise jwt.InvalidTokenError("Invalid token subject")

    return payload
