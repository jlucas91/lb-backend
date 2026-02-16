import httpx

from app.models.user import User


async def _setup(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> tuple[str, str, dict[str, str]]:
    """Create a production, a location, and add other_user as member.
    Returns (production_id, location_id, other_headers).
    """
    # Create production
    prod_resp = await authenticated_client.post(
        "/api/v1/productions", json={"name": "Loc Film"}
    )
    prod_id = prod_resp.json()["id"]

    # Create location
    loc_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "100 Test Spot Rd"}
    )
    loc_id = loc_resp.json()["id"]

    # Add other user to production
    await authenticated_client.post(
        f"/api/v1/productions/{prod_id}/members",
        json={"user_id": str(other_user.id), "role": "member"},
    )

    return prod_id, loc_id, other_auth_headers


async def test_add_location_to_production(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    prod_id, loc_id, _ = await _setup(
        authenticated_client, other_user, other_auth_headers
    )
    resp = await authenticated_client.post(
        f"/api/v1/productions/{prod_id}/locations",
        json={"location_id": loc_id},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "scouted"


async def test_list_production_locations(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    prod_id, loc_id, _ = await _setup(
        authenticated_client, other_user, other_auth_headers
    )
    await authenticated_client.post(
        f"/api/v1/productions/{prod_id}/locations",
        json={"location_id": loc_id},
    )
    resp = await authenticated_client.get(f"/api/v1/productions/{prod_id}/locations")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_update_production_location_status(
    authenticated_client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    prod_id, loc_id, _ = await _setup(
        authenticated_client, other_user, other_auth_headers
    )
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
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    prod_id, loc_id, _ = await _setup(
        authenticated_client, other_user, other_auth_headers
    )
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
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    prod_id, loc_id, other_hdrs = await _setup(
        authenticated_client, other_user, other_auth_headers
    )
    await authenticated_client.post(
        f"/api/v1/productions/{prod_id}/locations",
        json={"location_id": loc_id},
    )
    resp = await client.patch(
        f"/api/v1/productions/{prod_id}/locations/{loc_id}",
        json={"status": "approved"},
        headers=other_hdrs,
    )
    assert resp.status_code == 403
