import httpx

from app.models.user import User


async def test_create_project(
    authenticated_client: httpx.AsyncClient,
) -> None:
    resp = await authenticated_client.post(
        "/api/v1/projects",
        json={
            "name": "My Film",
            "description": "A great film",
            "project_type": "movie",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Film"
    assert data["project_type"] == "movie"
    assert data["status"] == "active"


async def test_list_projects(
    authenticated_client: httpx.AsyncClient,
) -> None:
    await authenticated_client.post(
        "/api/v1/projects", json={"name": "Film 1", "project_type": "movie"}
    )
    await authenticated_client.post(
        "/api/v1/projects", json={"name": "Film 2", "project_type": "tv_show"}
    )
    resp = await authenticated_client.get("/api/v1/projects")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_project(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/projects", json={"name": "Detail Film", "project_type": "movie"}
    )
    proj_id = create_resp.json()["id"]
    resp = await authenticated_client.get(f"/api/v1/projects/{proj_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Detail Film"


async def test_update_project(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/projects", json={"name": "Old Name", "project_type": "movie"}
    )
    proj_id = create_resp.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/projects/{proj_id}",
        json={"name": "New Name", "status": "wrapped"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["status"] == "wrapped"


async def test_delete_project(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/projects", json={"name": "To Delete", "project_type": "movie"}
    )
    proj_id = create_resp.json()["id"]
    resp = await authenticated_client.delete(f"/api/v1/projects/{proj_id}")
    assert resp.status_code == 204


async def test_auto_owner_membership(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/projects", json={"name": "Owner Test", "project_type": "movie"}
    )
    proj_id = create_resp.json()["id"]
    resp = await authenticated_client.get(f"/api/v1/projects/{proj_id}/members")
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"


async def test_non_member_cannot_access(
    client: httpx.AsyncClient,
    authenticated_client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/projects", json={"name": "Private Film", "project_type": "movie"}
    )
    proj_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/projects/{proj_id}", headers=other_auth_headers)
    assert resp.status_code == 404
