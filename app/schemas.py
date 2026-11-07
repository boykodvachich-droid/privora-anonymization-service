from pydantic import BaseModel, Field

class AnonymizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)

class AnonymizeResponse(BaseModel):
    anonymized_text: str
    detected: dict[str, int]
    processing_time_ms: float
