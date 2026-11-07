
import json
import os
import time
import logging

import pika


logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost:5672/%2F",
)

QUEUE_NAME = "datamask_anonymization"


def get_connection(max_retries: int = 5, delay: int = 2):
    """Connect to RabbitMQ with retries."""

    parameters = pika.URLParameters(RABBITMQ_URL)

    for attempt in range(max_retries):
        try:
            connection = pika.BlockingConnection(parameters)
            logger.info("Connected to RabbitMQ")
            return connection

        except pika.exceptions.AMQPConnectionError:
            logger.warning(
                "RabbitMQ connection attempt %s/%s failed",
                attempt + 1,
                max_retries,
            )

            if attempt + 1 == max_retries:
                raise

            time.sleep(delay)


def publish_task(task_id: str, text: str) -> None:
    """Publish an anonymization task to RabbitMQ."""

    connection = get_connection()

    try:
        channel = connection.channel()

        channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True,
        )

        message = {
            "task_id": task_id,
            "text": text,
        }

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(message, ensure_ascii=False),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )

        logger.info("Task %s published", task_id)

    finally:
        connection.close()
