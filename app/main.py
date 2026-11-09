
import os
import json
import hashlib
import uuid
from time import perf_counter

import redis
from fastapi import FastAPI, HTTPException, Query

from app.schemas import AnonymizeRequest, AnonymizeResponse
from app.anonymizer.engine import AnonymizationEngine
from app.queue.rabbitmq import publish_task
from app.database import SessionLocal
from app.models import Task


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

    categories_key = (
        sorted(payload.categories)
        if payload.categories is not None
        else None
    )

    cache_data = json.dumps(
        {
            "text": payload.text,
            "categories": categories_key,
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    cache_key = "datamask:" + hashlib.sha256(
        cache_data.encode("utf-8")
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

    result, detected = engine.anonymize(
        payload.text,
        categories=payload.categories,
    )

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

    # Сохраняем задачу в PostgreSQL
    db = SessionLocal()

    try:
        db_task = Task(
            id=task_id,
            status="pending",
            original_text=payload.text,
        )

        db.add(db_task)
        db.commit()

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Could not save task to database",
        ) from exc

    finally:
        db.close()

    # Redis — необязательный кэш
    try:
        redis_client.setex(
            f"datamask:task:{task_id}",
            TASK_RESULT_TTL,
            json.dumps(task_data, ensure_ascii=False),
        )
    except redis.RedisError:
        pass

    # Отправляем задачу в RabbitMQ независимо от Redis
    try:
        publish_task(task_id, payload.text)

    except Exception as exc:
        db = SessionLocal()

        try:
            failed_task = db.get(Task, task_id)

            if failed_task:
                failed_task.status = "failed"
                failed_task.original_text = ""
                db.commit()

        except Exception:
            db.rollback()

        finally:
            db.close()

        raise HTTPException(
            status_code=503,
            detail="Could not submit task for processing",
        ) from exc

    return task_data


@app.get("/api/v1/tasks")
def list_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Return recent tasks without exposing original text."""
    db = SessionLocal()

    try:
        tasks = (
            db.query(Task)
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "items": [
                {
                    "task_id": task.id,
                    "status": task.status,
                    "created_at": task.created_at,
                    "processing_time_ms": task.processing_time_ms,
                }
                for task in tasks
            ],
            "limit": limit,
            "offset": offset,
        }

    finally:
        db.close()


@app.get("/api/v1/tasks/{task_id}")
def get_task(task_id: str):
    # PostgreSQL — основной источник данных о задаче
    db = SessionLocal()

    try:
        task = db.get(Task, task_id)

        if task is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found",
            )

        return {
            "task_id": task.id,
            "status": task.status,
            "created_at": task.created_at,
            "anonymized_text": task.anonymized_text,
            "detected": (
                json.loads(task.detected)
                if task.detected
                else {}
            ),
            "processing_time_ms": task.processing_time_ms,
        }

    finally:
        db.close()


@app.delete("/api/v1/tasks/{task_id}")
def delete_task(task_id: str):
    """Delete a completed or failed task."""
    db = SessionLocal()

    try:
        task = db.get(Task, task_id)

        if task is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found",
            )

        if task.status not in ("completed", "failed"):
            raise HTTPException(
                status_code=409,
                detail="Only completed or failed tasks can be deleted",
            )

        db.delete(task)
        db.commit()

        return {
            "task_id": task_id,
            "status": "deleted",
        }

    finally:
        db.close()
