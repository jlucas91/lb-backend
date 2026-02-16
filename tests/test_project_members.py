import httpx

from app.models.user import User


async def _create_project(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/projects", json={"name": "Team Film", "project_type": "movie"}
    )
    return resp.json()["id"]


async def test_add_member(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
) -> None:
    proj_id = await _create_project(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"email": "other@example.com", "role": "member"},
    )
    assert resp.status_code == 201
    assert resp.json()["message"] == "Member added"


async def test_add_duplicate_member(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"email": "other@example.com"},
    )
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"email": "other@example.com"},
    )
    assert resp.status_code == 201


async def test_add_nonexistent_email(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 201


async def test_list_members_includes_user_info(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"email": "other@example.com"},
    )
    resp = await authenticated_client.get(f"/api/v1/projects/{proj_id}/members")
    assert resp.status_code == 200
    members = resp.json()
    # Should include the owner and the added member
    emails = {m["email"] for m in members}
    assert "other@example.com" in emails
    for m in members:
        assert "display_name" in m
        assert "email" in m


async def test_update_role(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"email": "other@example.com"},
    )
    resp = await authenticated_client.patch(
        f"/api/v1/projects/{proj_id}/members/{other_user.id}",
        json={"role": "manager"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "manager"


async def test_remove_member(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"email": "other@example.com"},
    )
    resp = await authenticated_client.delete(
        f"/api/v1/projects/{proj_id}/members/{other_user.id}"
    )
    assert resp.status_code == 204


async def test_member_cannot_change_roles(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
    test_user: User,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"email": "other@example.com"},
    )
    resp = await client.patch(
        f"/api/v1/projects/{proj_id}/members/{test_user.id}",
        json={"role": "member"},
        headers=other_auth_headers,
    )
    assert resp.status_code == 403
