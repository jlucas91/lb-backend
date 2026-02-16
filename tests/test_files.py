import uuid

import httpx

from app.models.user import User


async def test_request_upload(authenticated_client: httpx.AsyncClient) -> None:
    resp = await authenticated_client.post(
        "/api/v1/files/request-upload",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "file_id" in data
    assert "upload_url" in data
    assert "storage_key" in data


async def test_confirm_upload(authenticated_client: httpx.AsyncClient) -> None:
    # Request upload
    req_resp = await authenticated_client.post(
        "/api/v1/files/request-upload",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    file_id = req_resp.json()["file_id"]

    # Confirm
    resp = await authenticated_client.post(
        f"/api/v1/files/{file_id}/confirm",
        json={},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["size_bytes"] == 12345
    assert data["filename"] == "photo.jpg"


async def test_image_detection(authenticated_client: httpx.AsyncClient) -> None:
    resp = await authenticated_client.post(
        "/api/v1/files/request-upload",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    file_id = resp.json()["file_id"]

    confirm_resp = await authenticated_client.post(
        f"/api/v1/files/{file_id}/confirm",
        json={"width": 1920, "height": 1080},
    )
    data = confirm_resp.json()
    assert data["type"] == "image"
    assert data["width"] == 1920
    assert data["height"] == 1080


async def test_file_category_inference(
    authenticated_client: httpx.AsyncClient,
) -> None:
    for content_type, expected_category in [
        ("image/png", "photo"),
        ("video/mp4", "video"),
        ("application/pdf", "document"),
        ("application/octet-stream", "other"),
    ]:
        resp = await authenticated_client.post(
            "/api/v1/files/request-upload",
            json={"filename": "file.bin", "content_type": content_type},
        )
        file_id = resp.json()["file_id"]

        confirm_resp = await authenticated_client.post(
            f"/api/v1/files/{file_id}/confirm",
            json={},
        )
        assert confirm_resp.json()["file_category"] == expected_category


async def test_non_image_type(authenticated_client: httpx.AsyncClient) -> None:
    resp = await authenticated_client.post(
        "/api/v1/files/request-upload",
        json={"filename": "doc.pdf", "content_type": "application/pdf"},
    )
    file_id = resp.json()["file_id"]

    confirm_resp = await authenticated_client.post(
        f"/api/v1/files/{file_id}/confirm",
        json={},
    )
    assert confirm_resp.json()["type"] == "file"


async def test_get_file(authenticated_client: httpx.AsyncClient) -> None:
    req_resp = await authenticated_client.post(
        "/api/v1/files/request-upload",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    file_id = req_resp.json()["file_id"]
    await authenticated_client.post(f"/api/v1/files/{file_id}/confirm", json={})

    resp = await authenticated_client.get(f"/api/v1/files/{file_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "photo.jpg"
    assert data["download_url"] is not None


async def test_update_file(authenticated_client: httpx.AsyncClient) -> None:
    req_resp = await authenticated_client.post(
        "/api/v1/files/request-upload",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    file_id = req_resp.json()["file_id"]
    await authenticated_client.post(f"/api/v1/files/{file_id}/confirm", json={})

    resp = await authenticated_client.patch(
        f"/api/v1/files/{file_id}",
        json={"caption": "Nice photo", "sort_order": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["caption"] == "Nice photo"
    assert resp.json()["sort_order"] == 5


async def test_delete_file(authenticated_client: httpx.AsyncClient) -> None:
    req_resp = await authenticated_client.post(
        "/api/v1/files/request-upload",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    file_id = req_resp.json()["file_id"]
    await authenticated_client.post(f"/api/v1/files/{file_id}/confirm", json={})

    resp = await authenticated_client.delete(f"/api/v1/files/{file_id}")
    assert resp.status_code == 204

    # Verify deleted
    get_resp = await authenticated_client.get(f"/api/v1/files/{file_id}")
    assert get_resp.status_code == 404


async def test_confirm_nonexistent(authenticated_client: httpx.AsyncClient) -> None:
    fake_id = str(uuid.uuid4())
    resp = await authenticated_client.post(
        f"/api/v1/files/{fake_id}/confirm",
        json={},
    )
    assert resp.status_code == 404


async def test_cannot_confirm_others_file(
    authenticated_client: httpx.AsyncClient,
    client: httpx.AsyncClient,
    other_user: User,
    other_auth_headers: dict[str, str],
) -> None:
    # Create file as test user
    req_resp = await authenticated_client.post(
        "/api/v1/files/request-upload",
        json={"filename": "photo.jpg", "content_type": "image/jpeg"},
    )
    file_id = req_resp.json()["file_id"]

    # Other user tries to confirm — gets 404
    resp = await client.post(
        f"/api/v1/files/{file_id}/confirm",
        json={},
        headers=other_auth_headers,
    )
    assert resp.status_code == 404
