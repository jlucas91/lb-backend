import uuid

import httpx

from app.models.user import User


async def _create_project(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/projects", json={"name": "PL Project", "project_type": "movie"}
    )
    return resp.json()["id"]


async def _create_user_location(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/locations",
        json={
            "address": "100 User Location Blvd, Los Angeles, CA",
            "name": "User Location",
            "city": "Los Angeles",
            "state": "CA",
            "country": "US",
            "location_type": "commercial",
            "description": "A nice spot",
        },
    )
    return resp.json()["id"]


# --- Create ---


async def test_create_project_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={
            "address": "500 Warehouse Dr, Brooklyn, NY",
            "city": "Brooklyn",
            "state": "NY",
            "location_type": "industrial",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["address"] == "500 Warehouse Dr, Brooklyn, NY"
    assert data["city"] == "Brooklyn"
    assert data["location_type"] == "industrial"
    assert data["project_id"] == proj_id
    assert data["source_location_id"] is not None


# --- Copy ---


async def test_copy_user_location_to_project(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    loc_id = await _create_user_location(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations/copy",
        json={"location_id": loc_id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["address"] == "100 User Location Blvd, Los Angeles, CA"
    assert data["city"] == "Los Angeles"
    assert data["source_location_id"] == loc_id
    assert data["project_id"] == proj_id


async def test_copy_verifies_independence(
    authenticated_client: httpx.AsyncClient,
) -> None:
    """Editing a copied project location does not affect the user location."""
    proj_id = await _create_project(authenticated_client)
    loc_id = await _create_user_location(authenticated_client)
    copy_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations/copy",
        json={"location_id": loc_id},
    )
    pl_id = copy_resp.json()["id"]
    # Update project location
    await authenticated_client.patch(
        f"/api/v1/projects/{proj_id}/locations/{pl_id}",
        json={"address": "999 Renamed In Project St"},
    )
    # User location unchanged
    user_loc = await authenticated_client.get(f"/api/v1/locations/{loc_id}")
    assert user_loc.json()["address"] == "100 User Location Blvd, Los Angeles, CA"


async def test_copy_nonexistent_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations/copy",
        json={"location_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


# --- List ---


async def test_list_project_locations(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={"address": "10 Location A St"},
    )
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={"address": "20 Location B Ave"},
    )
    resp = await authenticated_client.get(f"/api/v1/projects/{proj_id}/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_list_project_locations_filter_type(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={"address": "1 Office Pkwy", "location_type": "commercial"},
    )
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={"address": "2 Park Blvd", "location_type": "outdoor"},
    )
    resp = await authenticated_client.get(
        f"/api/v1/projects/{proj_id}/locations",
        params={"location_type": "outdoor"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["address"] == "2 Park Blvd"


async def test_list_project_locations_search(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={"address": "Sunset Studio, Hollywood"},
    )
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={"address": "Downtown Loft, DTLA"},
    )
    resp = await authenticated_client.get(
        f"/api/v1/projects/{proj_id}/locations",
        params={"q": "sunset"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# --- Get ---


async def test_get_project_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={"address": "789 Get Me Rd", "description": "Detailed"},
    )
    pl_id = create_resp.json()["id"]
    resp = await authenticated_client.get(
        f"/api/v1/projects/{proj_id}/locations/{pl_id}"
    )
    assert resp.status_code == 200
    assert resp.json()["address"] == "789 Get Me Rd"
    assert resp.json()["description"] == "Detailed"


async def test_get_nonexistent_project_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    resp = await authenticated_client.get(
        f"/api/v1/projects/{proj_id}/locations/{uuid.uuid4()}"
    )
    assert resp.status_code == 404


# --- Update ---


async def test_update_project_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={"address": "Old Address Rd"},
    )
    pl_id = create_resp.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/projects/{proj_id}/locations/{pl_id}",
        json={"address": "New Address Ave", "city": "Chicago"},
    )
    assert resp.status_code == 200
    assert resp.json()["address"] == "New Address Ave"
    assert resp.json()["city"] == "Chicago"


# --- Delete ---


async def test_delete_project_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={"address": "Delete Me Dr"},
    )
    pl_id = create_resp.json()["id"]
    resp = await authenticated_client.delete(
        f"/api/v1/projects/{proj_id}/locations/{pl_id}"
    )
    assert resp.status_code == 204
    # Verify gone
    get_resp = await authenticated_client.get(
        f"/api/v1/projects/{proj_id}/locations/{pl_id}"
    )
    assert get_resp.status_code == 404


# --- Access control ---


async def test_non_member_cannot_access_project_locations(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    """Non-member gets 404 for project locations."""
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/locations",
        json={"address": "Secret Location Rd"},
    )
    resp = await client.get(
        f"/api/v1/projects/{proj_id}/locations",
        headers=other_auth_headers,
    )
    assert resp.status_code == 404
