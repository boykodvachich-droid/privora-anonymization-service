import json
import logging
import os
from time import perf_counter

import pika
import redis

from app.anonymizer.engine import AnonymizationEngine
from app.queue.rabbitmq import QUEUE_NAME, get_connection
from app.database import SessionLocal
from app.models import Task


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)

engine = AnonymizationEngine()

redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
)

TASK_RESULT_TTL = 3600


def process_task(channel, method, properties, body):
    """Process one anonymization task from RabbitMQ."""

    task_id = "unknown"
    started = perf_counter()

    db = SessionLocal()

    try:
        message = json.loads(body.decode("utf-8"))

        task_id = message["task_id"]
        text = message["text"]
        categories = message.get("categories")

        # Выполняем анонимизацию
        anonymized_text, detected = engine.anonymize(
            text,
            categories=categories,
        )

        processing_time_ms = round(
            (perf_counter() - started) * 1000,
            3,
        )

        # Находим задачу в PostgreSQL
        db_task = db.get(Task, task_id)

        if db_task is None:
            raise ValueError("Task not found in database")

        # Сохраняем результат и очищаем исходный текст
        db_task.status = "completed"
        db_task.anonymized_text = anonymized_text
        db_task.detected = json.dumps(
            detected,
            ensure_ascii=False,
        )
        db_task.processing_time_ms = processing_time_ms
        db_task.original_text = ""

        db.commit()

        # Формируем ответ для Redis
        result = {
            "task_id": task_id,
            "status": "completed",
            "anonymized_text": anonymized_text,
            "detected": detected,
            "processing_time_ms": processing_time_ms,
        }

        # Обновляем Redis
        try:
            redis_client.setex(
                f"datamask:task:{task_id}",
                TASK_RESULT_TTL,
                json.dumps(result, ensure_ascii=False),
            )
        except redis.RedisError:
            logger.warning(
                "Could not update Redis for task %s",
                task_id,
            )

        channel.basic_ack(
            delivery_tag=method.delivery_tag,
        )

        logger.info("Task %s completed", task_id)

    except Exception as exc:
        db.rollback()

        logger.error(
            "Task %s failed (%s)",
            task_id,
            type(exc).__name__,
        )

        # Сохраняем статус ошибки и очищаем исходный текст
        try:
            if task_id != "unknown":
                failed_task = db.get(Task, task_id)

                if failed_task is not None:
                    failed_task.status = "failed"
                    failed_task.original_text = ""
                    db.commit()

        except Exception as db_exc:
            db.rollback()

            logger.error(
                "Could not update failed task %s (%s)",
                task_id,
                type(db_exc).__name__,
            )

        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )

    finally:
        db.close()

def main():
    """Start the RabbitMQ worker."""

    connection = get_connection()
    channel = connection.channel()

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
    )

    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=process_task,
        auto_ack=False,
    )

    logger.info("Worker started. Waiting for tasks...")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Worker stopped")
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()
