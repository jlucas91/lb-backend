import httpx


async def _create_location(client: httpx.AsyncClient) -> str:
    resp = await client.post("/api/v1/locations", json={"name": "File Test Location"})
    return resp.json()["id"]


async def test_presign(authenticated_client: httpx.AsyncClient) -> None:
    loc_id = await _create_location(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files/presign",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "upload_url" in data
    assert "storage_key" in data


async def test_confirm_upload(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)
    presign_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files/presign",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    storage_key = presign_resp.json()["storage_key"]
    resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files/confirm",
        json={
            "storage_key": storage_key,
            "filename": "photo.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 12345,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_type"] == "photo"
    assert data["filename"] == "photo.jpg"


async def test_file_type_inference(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)
    for content_type, expected in [
        ("image/png", "photo"),
        ("video/mp4", "video"),
        ("application/pdf", "document"),
        ("application/octet-stream", "other"),
    ]:
        resp = await authenticated_client.post(
            f"/api/v1/locations/{loc_id}/files/confirm",
            json={
                "storage_key": f"uploads/test/{content_type}",
                "filename": "file.bin",
                "content_type": content_type,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["file_type"] == expected


async def test_list_files(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files/confirm",
        json={
            "storage_key": "uploads/a",
            "filename": "a.jpg",
            "content_type": "image/jpeg",
        },
    )
    await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files/confirm",
        json={
            "storage_key": "uploads/b",
            "filename": "b.pdf",
            "content_type": "application/pdf",
        },
    )
    resp = await authenticated_client.get(f"/api/v1/locations/{loc_id}/files")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_file(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files/confirm",
        json={
            "storage_key": "uploads/c",
            "filename": "c.jpg",
            "content_type": "image/jpeg",
        },
    )
    file_id = create_resp.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/locations/{loc_id}/files/{file_id}",
        json={"caption": "Nice photo", "sort_order": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["caption"] == "Nice photo"
    assert resp.json()["sort_order"] == 5


async def test_delete_file(
    authenticated_client: httpx.AsyncClient,
) -> None:
    loc_id = await _create_location(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/locations/{loc_id}/files/confirm",
        json={
            "storage_key": "uploads/d",
            "filename": "d.jpg",
            "content_type": "image/jpeg",
        },
    )
    file_id = create_resp.json()["id"]
    resp = await authenticated_client.delete(
        f"/api/v1/locations/{loc_id}/files/{file_id}"
    )
    assert resp.status_code == 204
