import httpx


async def test_register(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "display_name": "New User",
            "password": "secret123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["display_name"] == "New User"
    assert "id" in data


async def test_register_duplicate_email(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@example.com",
            "display_name": "First",
            "password": "secret123",
        },
    )
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@example.com",
            "display_name": "Second",
            "password": "secret456",
        },
    )
    assert resp.status_code == 409


async def test_login(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "display_name": "Login User",
            "password": "mypassword",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "mypassword"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "badpass@example.com",
            "display_name": "Bad",
            "password": "correct",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "badpass@example.com", "password": "wrong"},
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
