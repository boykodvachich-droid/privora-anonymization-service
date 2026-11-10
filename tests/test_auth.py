def test_register_normalizes_email_and_does_not_expose_password_hash(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "  NewUser@Example.com  ",
            "password": "Strong-test-password-123!",
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "password_hash" not in data
    assert "password" not in data


def test_register_rejects_duplicate_email(client, auth_headers):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "Another-strong-password-123!",
        },
    )

    assert response.status_code == 409


def test_login_rejects_wrong_password(client, auth_headers):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "owner@example.com",
            "password": "Wrong-password-123!",
        },
    )

    assert response.status_code == 401


def test_me_requires_valid_access_token(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json()["email"] == "owner@example.com"

    missing_token = client.get("/api/v1/auth/me")
    assert missing_token.status_code == 401

    invalid_token = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert invalid_token.status_code == 401


def test_users_cannot_access_or_delete_each_others_tasks(client, auth_headers):
    task_response = client.post(
        "/api/v1/tasks",
        json={"text": "Private task for the first user"},
        headers=auth_headers,
    )
    assert task_response.status_code == 200, task_response.text
    task_id = task_response.json()["task_id"]

    second_credentials = {
        "email": "second-user@example.com",
        "password": "Another-strong-password-456!",
    }

    register_response = client.post(
        "/api/v1/auth/register",
        json=second_credentials,
    )
    assert register_response.status_code == 201, register_response.text

    login_response = client.post(
        "/api/v1/auth/login",
        json=second_credentials,
    )
    assert login_response.status_code == 200, login_response.text

    second_headers = {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }

    detail_response = client.get(
        f"/api/v1/tasks/{task_id}",
        headers=second_headers,
    )
    assert detail_response.status_code == 404

    delete_response = client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=second_headers,
    )
    assert delete_response.status_code == 404

    owner_response = client.get(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
    )
    assert owner_response.status_code == 200
