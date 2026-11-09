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
DLQ_NAME = "datamask_anonymization_dead"


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


def declare_queues(channel):
    """Declare durable task and dead-letter queues."""

    channel.queue_declare(
        queue=DLQ_NAME,
        durable=True,
    )

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
    )


def publish_task(
    task_id: str,
    categories: list[str] | None = None,
) -> None:
    """Publish a task ID and categories without original text."""

    connection = get_connection()

    try:
        channel = connection.channel()

        declare_queues(channel)
        channel.confirm_delivery()

        message = {
            "task_id": task_id,
            "categories": categories,
        }

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(message, ensure_ascii=False),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
            mandatory=True,
        )

        logger.info("Published task %s to RabbitMQ", task_id)

    finally:
        connection.close()
