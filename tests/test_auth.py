import httpx

from app.models.user import User


async def test_register_endpoint_removed(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "display_name": "New User",
            "password": "secret123",
        },
    )
    assert resp.status_code == 404


async def test_login(client: httpx.AsyncClient, test_user: User) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: httpx.AsyncClient, test_user: User) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


async def test_get_me(authenticated_client: httpx.AsyncClient) -> None:
    resp = await authenticated_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"


async def test_update_me(authenticated_client: httpx.AsyncClient) -> None:
    resp = await authenticated_client.patch(
        "/api/v1/auth/me", json={"display_name": "Updated Name"}
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Updated Name"


async def test_update_password_requires_current(
    authenticated_client: httpx.AsyncClient,
) -> None:
    resp = await authenticated_client.patch(
        "/api/v1/auth/me", json={"password": "newpassword123"}
    )
    assert resp.status_code == 400


async def test_update_password_wrong_current(
    authenticated_client: httpx.AsyncClient,
) -> None:
    resp = await authenticated_client.patch(
        "/api/v1/auth/me",
        json={"password": "newpassword123", "current_password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_update_password_success(
    authenticated_client: httpx.AsyncClient,
) -> None:
    resp = await authenticated_client.patch(
        "/api/v1/auth/me",
        json={"password": "newpassword123", "current_password": "testpass123"},
    )
    assert resp.status_code == 200
