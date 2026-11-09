import json
from types import SimpleNamespace

from app.models import Task
from app.queue import worker


def test_worker_processes_task(db_session, monkeypatch):
    task_id = "11111111-1111-1111-1111-111111111111"

    task = Task(
        id=task_id,
        status="pending",
        original_text="Contact ivan@example.com",
    )

    db_session.add(task)
    db_session.commit()

    monkeypatch.setattr(
        worker,
        "SessionLocal",
        lambda: db_session,
    )

    monkeypatch.setattr(
        worker.redis_client,
        "setex",
        lambda *args, **kwargs: None,
    )

    channel = SimpleNamespace(
        basic_ack=lambda **kwargs: setattr(
            channel,
            "acked",
            kwargs["delivery_tag"],
        )
    )

    method = SimpleNamespace(delivery_tag=123)

    body = json.dumps({
        "task_id": task_id,
        "categories": None,
    }).encode("utf-8")

    worker.process_task(channel, method, None, body)

    db_session.expire_all()
    saved_task = db_session.get(Task, task_id)

    assert saved_task.status == "completed"
    assert saved_task.anonymized_text == "Contact i***@example.com"
    assert saved_task.detected == '{"EMAIL": 1}'
    assert saved_task.original_text == ""
    assert channel.acked == 123


def test_worker_marks_missing_task_as_failed(db_session, monkeypatch):
    monkeypatch.setattr(
        worker,
        "SessionLocal",
        lambda: db_session,
    )

    channel = SimpleNamespace(
        basic_nack=lambda **kwargs: setattr(
            channel,
            "nacked",
            kwargs["delivery_tag"],
        )
    )

    method = SimpleNamespace(delivery_tag=456)

    body = json.dumps({
        "task_id": "22222222-2222-2222-2222-222222222222",
        "categories": None,
    }).encode("utf-8")

    worker.process_task(channel, method, None, body)

    assert channel.nacked == 456
