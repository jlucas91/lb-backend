import httpx

from app.models.user import User


async def test_share_location(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
) -> None:
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "100 Shared St"}
    )
    loc_id = loc_resp.json()["id"]
    resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": str(other_user.id), "permission": "view"},
    )
    assert resp.status_code == 201
    assert resp.json()["permission"] == "view"


async def test_share_duplicate(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
) -> None:
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "200 Dup Share Ave"}
    )
    loc_id = loc_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": str(other_user.id)},
    )
    resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": str(other_user.id)},
    )
    assert resp.status_code == 409


async def test_list_shares(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
) -> None:
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "300 List Shares Blvd"}
    )
    loc_id = loc_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": str(other_user.id)},
    )
    resp = await authenticated_client.get(f"/api/v1/locations/{loc_id}/shares")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_revoke_share(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
) -> None:
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "400 Revoke Rd"}
    )
    loc_id = loc_resp.json()["id"]
    share_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": str(other_user.id)},
    )
    share_id = share_resp.json()["id"]
    resp = await authenticated_client.delete(
        f"/api/v1/locations/{loc_id}/shares/{share_id}"
    )
    assert resp.status_code == 204


async def test_shared_with_me(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "500 Shared To Me Ln"}
    )
    loc_id = loc_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": str(other_user.id)},
    )
    resp = await client.get("/api/v1/shared-with-me", headers=other_auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_shared_user_can_read_location(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "600 Readable Ave"}
    )
    loc_id = loc_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": str(other_user.id), "permission": "view"},
    )
    resp = await client.get(f"/api/v1/locations/{loc_id}", headers=other_auth_headers)
    assert resp.status_code == 200
    assert resp.json()["address"] == "600 Readable Ave"
