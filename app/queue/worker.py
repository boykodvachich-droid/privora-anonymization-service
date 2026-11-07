
import json
import logging
import os

import pika
import redis

from app.anonymizer.engine import AnonymizationEngine
from app.queue.rabbitmq import QUEUE_NAME, get_connection


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

TASK_RESULT_TTL = 3600  # 1 hour


def process_task(channel, method, properties, body):
    """Process one anonymization task from RabbitMQ."""

    task_id = "unknown"

    try:
        message = json.loads(body.decode("utf-8"))

        task_id = message["task_id"]
        text = message["text"]

        anonymized_text, detected = engine.anonymize(text)

        result = {
            "task_id": task_id,
            "status": "completed",
            "anonymized_text": anonymized_text,
            "detected": detected,
        }

        redis_client.setex(
            f"datamask:task:{task_id}",
            TASK_RESULT_TTL,
            json.dumps(result, ensure_ascii=False),
        )

        channel.basic_ack(delivery_tag=method.delivery_tag)

        logger.info("Task %s completed", task_id)

    except Exception:
        logger.exception("Task %s failed", task_id)

        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )


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
