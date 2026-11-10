def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "datamask",
    }


def test_anonymize_endpoint(client):
    response = client.post(
        "/api/v1/anonymize",
        json={"text": "Contact ivan@example.com"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["anonymized_text"] == "Contact i***@example.com"
    assert data["detected"] == {"EMAIL": 1}
    assert data["processing_time_ms"] >= 0


def test_create_task_endpoint(client, auth_headers):
    response = client.post(
        "/api/v1/tasks",
        json={"text": "Contact ivan@example.com"},
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "pending"
    assert "task_id" in data


def test_get_task_endpoint(client, auth_headers):
    create_response = client.post(
        "/api/v1/tasks",
        json={"text": "Contact ivan@example.com"},
        headers=auth_headers,
    )

    task_id = create_response.json()["task_id"]

    response = client.get(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["task_id"] == task_id
    assert data["status"] == "pending"
    assert data["anonymized_text"] is None
    assert data["detected"] == {}


def test_get_nonexistent_task(client, auth_headers):
    response = client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_task_endpoints_require_authentication(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={"text": "Contact ivan@example.com"},
    )
    list_response = client.get("/api/v1/tasks")
    detail_response = client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000"
    )
    delete_response = client.delete(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000"
    )

    assert create_response.status_code == 401
    assert list_response.status_code == 401
    assert detail_response.status_code == 401
    assert delete_response.status_code == 401


def test_anonymize_rejects_empty_text(client):
    response = client.post(
        "/api/v1/anonymize",
        json={"text": ""},
    )

    assert response.status_code == 422


def test_create_task_clears_original_text_when_publish_fails(
    client, db_session, monkeypatch, auth_headers
):
    from app import main

    created_task_ids = []

    def fail_publish(task_id, text):
        created_task_ids.append(task_id)
        raise RuntimeError("RabbitMQ unavailable")

    monkeypatch.setattr(main, "publish_task", fail_publish)

    response = client.post(
        "/api/v1/tasks",
        json={"text": "Sensitive information test@example.com"},
        headers=auth_headers,
    )

    assert response.status_code == 503
    assert len(created_task_ids) == 1

    failed_task = db_session.get(main.Task, created_task_ids[0])

    assert failed_task is not None
    assert failed_task.status == "failed"
    assert failed_task.original_text == ""
