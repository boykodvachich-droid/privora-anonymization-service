
import os
import json
import hashlib
from time import perf_counter

import redis
from fastapi import FastAPI

from app.schemas import AnonymizeRequest, AnonymizeResponse
from app.anonymizer.engine import AnonymizationEngine


app = FastAPI(
    title="DataMask API",
    description="Service for detecting and masking sensitive information in text.",
    version="0.1.0",
)

engine = AnonymizationEngine()

# Redis connection
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

CACHE_TTL = 300  # 5 minutes


@app.get("/health")
def health():
    return {"status": "ok", "service": "datamask"}


@app.post("/api/v1/anonymize", response_model=AnonymizeResponse)
def anonymize(payload: AnonymizeRequest):
    started = perf_counter()

    # Create a hash instead of storing the original text in the cache key.
    cache_key = "datamask:" + hashlib.sha256(
        payload.text.encode("utf-8")
    ).hexdigest()

    # Try to get the result from Redis.
    try:
        cached_result = redis_client.get(cache_key)

        if cached_result:
            cached_data = json.loads(cached_result)

            elapsed_ms = round(
                (perf_counter() - started) * 1000, 3
            )

            return AnonymizeResponse(
                anonymized_text=cached_data["anonymized_text"],
                detected=cached_data["detected"],
                processing_time_ms=elapsed_ms,
            )

    except (redis.RedisError, ValueError):
        pass

    # If cache is unavailable or empty, anonymize normally.
    result, detected = engine.anonymize(payload.text)

    elapsed_ms = round(
        (perf_counter() - started) * 1000, 3
    )

    response = AnonymizeResponse(
        anonymized_text=result,
        detected=detected,
        processing_time_ms=elapsed_ms,
    )

    # Try to save the result in Redis.
    try:
        redis_client.setex(
            cache_key,
            CACHE_TTL,
            json.dumps({
                "anonymized_text": result,
                "detected": detected,
            }, ensure_ascii=False),
        )

    except redis.RedisError:
        pass

    return response
