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