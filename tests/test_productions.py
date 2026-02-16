import httpx

from app.models.user import User


async def test_create_production(
    authenticated_client: httpx.AsyncClient,
) -> None:
    resp = await authenticated_client.post(
        "/api/v1/productions",
        json={"name": "My Film", "description": "A great film"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Film"
    assert data["status"] == "active"


async def test_list_productions(
    authenticated_client: httpx.AsyncClient,
) -> None:
    await authenticated_client.post("/api/v1/productions", json={"name": "Film 1"})
    await authenticated_client.post("/api/v1/productions", json={"name": "Film 2"})
    resp = await authenticated_client.get("/api/v1/productions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_production(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/productions", json={"name": "Detail Film"}
    )
    prod_id = create_resp.json()["id"]
    resp = await authenticated_client.get(f"/api/v1/productions/{prod_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Detail Film"


async def test_update_production(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/productions", json={"name": "Old Name"}
    )
    prod_id = create_resp.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/productions/{prod_id}",
        json={"name": "New Name", "status": "wrapped"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["status"] == "wrapped"


async def test_delete_production(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/productions", json={"name": "To Delete"}
    )
    prod_id = create_resp.json()["id"]
    resp = await authenticated_client.delete(f"/api/v1/productions/{prod_id}")
    assert resp.status_code == 204


async def test_auto_owner_membership(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/productions", json={"name": "Owner Test"}
    )
    prod_id = create_resp.json()["id"]
    resp = await authenticated_client.get(f"/api/v1/productions/{prod_id}/members")
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
    # Create production as test user
    create_resp = await authenticated_client.post(
        "/api/v1/productions", json={"name": "Private Film"}
    )
    prod_id = create_resp.json()["id"]

    # Other user tries to access
    resp = await client.get(
        f"/api/v1/productions/{prod_id}", headers=other_auth_headers
    )
    assert resp.status_code == 404
