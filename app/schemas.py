from datetime import datetime
from pydantic import BaseModel, Field, field_validator

ALLOWED_CATEGORIES = {
    "BANK_CARD",
    "INN",
    "PASSPORT",
    "SNILS",
    "EMAIL",
    "DATE",
    "ADDRESS",
    "PERSON",
    "PHONE",
}


class AnonymizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)
    categories: list[str] | None = None

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, value):
        if value is not None:
            unknown = set(value) - ALLOWED_CATEGORIES
            if unknown:
                raise ValueError(
                    f"Unknown categories: {', '.join(sorted(unknown))}"
                )
        return value


class AnonymizeResponse(BaseModel):
    anonymized_text: str
    detected: dict[str, int]
    processing_time_ms: float

class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        import re

        value = value.strip().lower()

        if not re.fullmatch(
            r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+",
            value,
        ):
            raise ValueError("Invalid email address")

        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime
