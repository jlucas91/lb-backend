import httpx


async def _setup(
    client: httpx.AsyncClient,
    authenticated_client: httpx.AsyncClient,
) -> tuple[str, str, str, dict[str, str]]:
    """Create a production, a location, and a second user as member.
    Returns (production_id, location_id, other_user_id, other_headers).
    """
    # Create production
    prod_resp = await authenticated_client.post(
        "/api/v1/productions", json={"name": "Loc Film"}
    )
    prod_id = prod_resp.json()["id"]

    # Create location
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"name": "Test Spot"}
    )
    loc_id = loc_resp.json()["id"]

    # Create another user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "plmember@example.com",
            "display_name": "PL Member",
            "password": "pass123",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "plmember@example.com", "password": "pass123"},
    )
    token = login_resp.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}
    me_resp = await client.get("/api/v1/auth/me", headers=other_headers)
    other_user_id = me_resp.json()["id"]

    # Add other user to production
    await authenticated_client.post(
        f"/api/v1/productions/{prod_id}/members",
        json={"user_id": other_user_id, "role": "member"},
    )

    return prod_id, loc_id, other_user_id, other_headers


async def test_add_location_to_production(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    prod_id, loc_id, _, _ = await _setup(client, authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/productions/{prod_id}/locations",
        json={"location_id": loc_id},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "scouted"


async def test_list_production_locations(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    prod_id, loc_id, _, _ = await _setup(client, authenticated_client)
    await authenticated_client.post(
        f"/api/v1/productions/{prod_id}/locations",
        json={"location_id": loc_id},
    )
    resp = await authenticated_client.get(f"/api/v1/productions/{prod_id}/locations")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_update_production_location_status(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    prod_id, loc_id, _, _ = await _setup(client, authenticated_client)
    await authenticated_client.post(
        f"/api/v1/productions/{prod_id}/locations",
        json={"location_id": loc_id},
    )
    resp = await authenticated_client.patch(
        f"/api/v1/productions/{prod_id}/locations/{loc_id}",
        json={"status": "approved"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


async def test_remove_production_location(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    prod_id, loc_id, _, _ = await _setup(client, authenticated_client)
    await authenticated_client.post(
        f"/api/v1/productions/{prod_id}/locations",
        json={"location_id": loc_id},
    )
    resp = await authenticated_client.delete(
        f"/api/v1/productions/{prod_id}/locations/{loc_id}"
    )
    assert resp.status_code == 204


async def test_member_cannot_update_status(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    prod_id, loc_id, _, other_headers = await _setup(client, authenticated_client)
    await authenticated_client.post(
        f"/api/v1/productions/{prod_id}/locations",
        json={"location_id": loc_id},
    )
    resp = await client.patch(
        f"/api/v1/productions/{prod_id}/locations/{loc_id}",
        json={"status": "approved"},
        headers=other_headers,
    )
    assert resp.status_code == 403
