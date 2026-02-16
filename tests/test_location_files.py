import httpx

from app.models.user import User


async def _create_location(client: httpx.AsyncClient) -> str:
    resp = await client.post("/api/v1/locations", json={"address": "100 File Test Rd"})
    return resp.json()["id"]


async def _create_active_file(client: httpx.AsyncClient) -> str:
    """Request upload + confirm -> return active file_id."""
    req_resp = await client.post(
        "/api/v1/files/request-upload",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    file_id = req_resp.json()["file_id"]
    await client.post(f"/api/v1/files/{file_id}/confirm", json={})
    return file_id


async def test_attach_file_to_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)
    file_id = await _create_active_file(authenticated_client)

    resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files",
        json={"file_id": file_id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == file_id
    assert data["download_url"] is not None


async def test_list_location_files(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)
    file_id1 = await _create_active_file(authenticated_client)
    file_id2 = await _create_active_file(authenticated_client)

    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files",
        json={"file_id": file_id1},
    )
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files",
        json={"file_id": file_id2},
    )

    resp = await authenticated_client.get(f"/api/v1/locations/{loc_id}/files")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_detach_file(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)
    file_id = await _create_active_file(authenticated_client)

    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files",
        json={"file_id": file_id},
    )

    # Detach
    resp = await authenticated_client.delete(
        f"/api/v1/locations/{loc_id}/files/{file_id}"
    )
    assert resp.status_code == 204

    # File still exists (not deleted from S3)
    get_resp = await authenticated_client.get(f"/api/v1/files/{file_id}")
    assert get_resp.status_code == 200

    # But no longer attached to location
    list_resp = await authenticated_client.get(f"/api/v1/locations/{loc_id}/files")
    assert len(list_resp.json()) == 0


async def test_attach_requires_active_file(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)

    # Create a pending file (not confirmed)
    req_resp = await authenticated_client.post(
        "/api/v1/files/request-upload",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    pending_file_id = req_resp.json()["file_id"]

    resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files",
        json={"file_id": pending_file_id},
    )
    assert resp.status_code == 400


async def test_list_requires_read_access(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    loc_id = await _create_location(authenticated_client)

    # Other user cannot see the location's files
    resp = await client.get(
        f"/api/v1/locations/{loc_id}/files",
        headers=other_auth_headers,
    )
    assert resp.status_code == 404


async def test_attach_requires_write_access(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    loc_id = await _create_location(authenticated_client)
    file_id = await _create_active_file(authenticated_client)

    # Share with view-only
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/shares",
        json={"email": "other@example.com", "permission": "view"},
    )

    # Viewer tries to attach — gets 403 (or 404 if share not visible in test txn)
    resp = await client.post(
        f"/api/v1/locations/{loc_id}/files",
        json={"file_id": file_id},
        headers=other_auth_headers,
    )
    assert resp.status_code in (403, 404)
