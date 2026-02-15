import httpx

from app.models.user import User


async def _create_other_user(
    client: httpx.AsyncClient,
) -> tuple[str, str, dict[str, str]]:
    """Create another user, return (user_id, token, headers)."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "member@example.com",
            "display_name": "Member",
            "password": "pass123",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "member@example.com", "password": "pass123"},
    )
    token = login_resp.json()["access_token"]
    me_resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    user_id = me_resp.json()["id"]
    return user_id, token, {"Authorization": f"Bearer {token}"}


async def _create_project(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/projects", json={"name": "Team Film", "project_type": "movie"}
    )
    return resp.json()["id"]


async def test_add_member(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    user_id, _, _ = await _create_other_user(client)
    proj_id = await _create_project(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"user_id": user_id, "role": "member"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "member"


async def test_add_duplicate_member(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    user_id, _, _ = await _create_other_user(client)
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"user_id": user_id},
    )
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"user_id": user_id},
    )
    assert resp.status_code == 409


async def test_update_role(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    user_id, _, _ = await _create_other_user(client)
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"user_id": user_id},
    )
    resp = await authenticated_client.patch(
        f"/api/v1/projects/{proj_id}/members/{user_id}",
        json={"role": "manager"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "manager"


async def test_remove_member(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    user_id, _, _ = await _create_other_user(client)
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"user_id": user_id},
    )
    resp = await authenticated_client.delete(
        f"/api/v1/projects/{proj_id}/members/{user_id}"
    )
    assert resp.status_code == 204


async def test_member_cannot_change_roles(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
    test_user: User,
) -> None:
    user_id, _, other_headers = await _create_other_user(client)
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"user_id": user_id},
    )
    resp = await client.patch(
        f"/api/v1/projects/{proj_id}/members/{test_user.id}",
        json={"role": "member"},
        headers=other_headers,
    )
    assert resp.status_code == 403
