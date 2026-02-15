import httpx


async def _create_project(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/projects", json={"name": "Folder Project", "project_type": "movie"}
    )
    return resp.json()["id"]


async def test_create_folder(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/folders",
        json={"name": "Root Folder"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Root Folder"
    assert data["parent_id"] is None


async def test_create_nested_folder(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    parent_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/folders",
        json={"name": "Parent"},
    )
    parent_id = parent_resp.json()["id"]
    child_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/folders",
        json={"name": "Child", "parent_id": parent_id},
    )
    assert child_resp.status_code == 201
    assert child_resp.json()["parent_id"] == parent_id


async def test_list_folders(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/folders",
        json={"name": "Folder 1"},
    )
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/folders",
        json={"name": "Folder 2"},
    )
    resp = await authenticated_client.get(f"/api/v1/projects/{proj_id}/folders")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_folder(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/folders",
        json={"name": "Old Folder"},
    )
    folder_id = create_resp.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/projects/{proj_id}/folders/{folder_id}",
        json={"name": "New Folder"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Folder"


async def test_delete_folder(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/folders",
        json={"name": "To Delete"},
    )
    folder_id = create_resp.json()["id"]
    resp = await authenticated_client.delete(
        f"/api/v1/projects/{proj_id}/folders/{folder_id}"
    )
    assert resp.status_code == 204


async def test_self_parent_prevention(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/folders",
        json={"name": "Self Folder"},
    )
    folder_id = create_resp.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/projects/{proj_id}/folders/{folder_id}",
        json={"parent_id": folder_id},
    )
    assert resp.status_code == 400
