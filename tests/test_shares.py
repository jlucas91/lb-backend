import httpx


async def _create_other_user(
    client: httpx.AsyncClient,
) -> tuple[str, dict[str, str]]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "shareuser@example.com",
            "display_name": "Share User",
            "password": "pass123",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "shareuser@example.com", "password": "pass123"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    return me_resp.json()["id"], headers


async def test_share_location(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    other_id, _ = await _create_other_user(client)
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "100 Shared St"}
    )
    loc_id = loc_resp.json()["id"]
    resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": other_id, "permission": "view"},
    )
    assert resp.status_code == 201
    assert resp.json()["permission"] == "view"


async def test_share_duplicate(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    other_id, _ = await _create_other_user(client)
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "200 Dup Share Ave"}
    )
    loc_id = loc_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": other_id},
    )
    resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": other_id},
    )
    assert resp.status_code == 409


async def test_list_shares(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    other_id, _ = await _create_other_user(client)
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "300 List Shares Blvd"}
    )
    loc_id = loc_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": other_id},
    )
    resp = await authenticated_client.get(f"/api/v1/locations/{loc_id}/shares")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_revoke_share(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    other_id, _ = await _create_other_user(client)
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "400 Revoke Rd"}
    )
    loc_id = loc_resp.json()["id"]
    share_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": other_id},
    )
    share_id = share_resp.json()["id"]
    resp = await authenticated_client.delete(
        f"/api/v1/locations/{loc_id}/shares/{share_id}"
    )
    assert resp.status_code == 204


async def test_shared_with_me(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    other_id, other_headers = await _create_other_user(client)
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "500 Shared To Me Ln"}
    )
    loc_id = loc_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": other_id},
    )
    resp = await client.get("/api/v1/shared-with-me", headers=other_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_shared_user_can_read_location(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    other_id, other_headers = await _create_other_user(client)
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "600 Readable Ave"}
    )
    loc_id = loc_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"shared_with_id": other_id, "permission": "view"},
    )
    resp = await client.get(f"/api/v1/locations/{loc_id}", headers=other_headers)
    assert resp.status_code == 200
    assert resp.json()["address"] == "600 Readable Ave"
