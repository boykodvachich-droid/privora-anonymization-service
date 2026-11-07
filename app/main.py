
import os
import json
import hashlib
import uuid
from time import perf_counter

import redis
from fastapi import FastAPI, HTTPException

from app.schemas import AnonymizeRequest, AnonymizeResponse
from app.anonymizer.engine import AnonymizationEngine
from app.queue.rabbitmq import publish_task


app = FastAPI(
    title="DataMask API",
    description="Service for detecting and masking sensitive information in text.",
    version="0.1.0",
)

engine = AnonymizationEngine()

redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

CACHE_TTL = 300
TASK_RESULT_TTL = 3600


@app.get("/health")
def health():
    return {"status": "ok", "service": "datamask"}


@app.post("/api/v1/anonymize", response_model=AnonymizeResponse)
def anonymize(payload: AnonymizeRequest):
    started = perf_counter()

    cache_key = "datamask:" + hashlib.sha256(
        payload.text.encode("utf-8")
    ).hexdigest()

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

    result, detected = engine.anonymize(payload.text)

    elapsed_ms = round(
        (perf_counter() - started) * 1000, 3
    )

    response = AnonymizeResponse(
        anonymized_text=result,
        detected=detected,
        processing_time_ms=elapsed_ms,
    )

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


@app.post("/api/v1/tasks")
def create_task(payload: AnonymizeRequest):
    task_id = str(uuid.uuid4())

    task_data = {
        "task_id": task_id,
        "status": "pending",
    }

    try:
        redis_client.setex(
            f"datamask:task:{task_id}",
            TASK_RESULT_TTL,
            json.dumps(task_data, ensure_ascii=False),
        )

        publish_task(task_id, payload.text)

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not submit task for processing",
        ) from exc

    return task_data


@app.get("/api/v1/tasks/{task_id}")
def get_task(task_id: str):
    try:
        task_data = redis_client.get(
            f"datamask:task:{task_id}"
        )
    except redis.RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="Task storage is unavailable",
        ) from exc

    if not task_data:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return json.loads(task_data)
