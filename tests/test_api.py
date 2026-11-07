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


def test_create_task_endpoint(client):
    response = client.post(
        "/api/v1/tasks",
        json={"text": "Contact ivan@example.com"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "pending"
    assert "task_id" in data


def test_get_task_endpoint(client):
    create_response = client.post(
        "/api/v1/tasks",
        json={"text": "Contact ivan@example.com"},
    )

    task_id = create_response.json()["task_id"]

    response = client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["task_id"] == task_id
    assert data["status"] == "pending"
    assert data["anonymized_text"] is None
    assert data["detected"] == {}


def test_get_nonexistent_task(client):
    response = client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_anonymize_rejects_empty_text(client):
    response = client.post(
        "/api/v1/anonymize",
        json={"text": ""},
    )

    assert response.status_code == 422