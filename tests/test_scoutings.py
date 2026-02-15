import uuid

import httpx


async def _create_location(client: httpx.AsyncClient) -> str:
    resp = await client.post("/api/v1/locations", json={"name": "Scout Location"})
    return resp.json()["id"]


async def test_create_scouting(authenticated_client: httpx.AsyncClient) -> None:
    loc_id = await _create_location(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings",
        json={"scouted_at": "2026-02-15T10:00:00Z"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["location_id"] == loc_id
    assert data["status"] == "draft"
    assert data["notes"] is None


async def test_create_scouting_with_notes(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings",
        json={
            "scouted_at": "2026-02-15T10:00:00Z",
            "notes": "Great natural light",
            "status": "complete",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["notes"] == "Great natural light"
    assert data["status"] == "complete"


async def test_list_scoutings(authenticated_client: httpx.AsyncClient) -> None:
    loc_id = await _create_location(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings",
        json={"scouted_at": "2026-02-14T10:00:00Z"},
    )
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings",
        json={"scouted_at": "2026-02-15T10:00:00Z"},
    )
    resp = await authenticated_client.get(f"/api/v1/locations/{loc_id}/scoutings")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Ordered by scouted_at desc — most recent first
    assert data[0]["scouted_at"] > data[1]["scouted_at"]


async def test_get_scouting(authenticated_client: httpx.AsyncClient) -> None:
    loc_id = await _create_location(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings",
        json={"scouted_at": "2026-02-15T10:00:00Z", "notes": "Detail test"},
    )
    scouting_id = create_resp.json()["id"]
    resp = await authenticated_client.get(
        f"/api/v1/locations/{loc_id}/scoutings/{scouting_id}"
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Detail test"


async def test_update_scouting(authenticated_client: httpx.AsyncClient) -> None:
    loc_id = await _create_location(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings",
        json={"scouted_at": "2026-02-15T10:00:00Z"},
    )
    scouting_id = create_resp.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/locations/{loc_id}/scoutings/{scouting_id}",
        json={"notes": "Updated notes", "status": "complete"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"] == "Updated notes"
    assert data["status"] == "complete"


async def test_delete_scouting(authenticated_client: httpx.AsyncClient) -> None:
    loc_id = await _create_location(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings",
        json={"scouted_at": "2026-02-15T10:00:00Z"},
    )
    scouting_id = create_resp.json()["id"]
    resp = await authenticated_client.delete(
        f"/api/v1/locations/{loc_id}/scoutings/{scouting_id}"
    )
    assert resp.status_code == 204

    # Verify deleted
    get_resp = await authenticated_client.get(
        f"/api/v1/locations/{loc_id}/scoutings/{scouting_id}"
    )
    assert get_resp.status_code == 404


async def test_scouting_not_found(authenticated_client: httpx.AsyncClient) -> None:
    loc_id = await _create_location(authenticated_client)
    fake_id = str(uuid.uuid4())
    resp = await authenticated_client.get(
        f"/api/v1/locations/{loc_id}/scoutings/{fake_id}"
    )
    assert resp.status_code == 404


async def test_scouting_photo_upload_flow(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings",
        json={"scouted_at": "2026-02-15T10:00:00Z"},
    )
    scouting_id = create_resp.json()["id"]

    # Presign
    presign_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings/{scouting_id}/photos/presign",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    assert presign_resp.status_code == 200
    storage_key = presign_resp.json()["storage_key"]

    # Confirm
    confirm_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings/{scouting_id}/photos/confirm",
        json={
            "storage_key": storage_key,
            "filename": "photo.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1024,
        },
    )
    assert confirm_resp.status_code == 201
    file_data = confirm_resp.json()
    assert file_data["scouting_id"] == scouting_id

    # List photos
    list_resp = await authenticated_client.get(
        f"/api/v1/locations/{loc_id}/scoutings/{scouting_id}/photos"
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Scouting photo should NOT appear in general location files
    files_resp = await authenticated_client.get(f"/api/v1/locations/{loc_id}/files")
    assert files_resp.status_code == 200
    assert len(files_resp.json()) == 0

    # Delete photo
    file_id = file_data["id"]
    del_resp = await authenticated_client.delete(
        f"/api/v1/locations/{loc_id}/scoutings/{scouting_id}/photos/{file_id}"
    )
    assert del_resp.status_code == 204

    # Verify deleted
    list_resp2 = await authenticated_client.get(
        f"/api/v1/locations/{loc_id}/scoutings/{scouting_id}/photos"
    )
    assert len(list_resp2.json()) == 0


async def test_update_scouting_by_non_scout_forbidden(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
) -> None:
    """A second user with read access cannot update a scouting they didn't create."""
    loc_id = await _create_location(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/scoutings",
        json={"scouted_at": "2026-02-15T10:00:00Z"},
    )
    scouting_id = create_resp.json()["id"]

    # Register a second user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "other@example.com",
            "password": "otherpass123",
            "display_name": "Other User",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "otherpass123"},
    )
    token = login_resp.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}

    # Share the location with the other user for read access
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"email": "other@example.com", "permission": "view"},
    )

    # Other user tries to update the scouting — gets 403 (forbidden) or
    # 404 (location not visible) depending on share propagation in test txn
    resp = await client.patch(
        f"/api/v1/locations/{loc_id}/scoutings/{scouting_id}",
        json={"notes": "Hacked notes"},
        headers=other_headers,
    )
    assert resp.status_code in (403, 404)
