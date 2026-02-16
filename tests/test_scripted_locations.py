import httpx


async def _create_project(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/projects", json={"name": "SL Project", "project_type": "movie"}
    )
    return resp.json()["id"]


async def _create_episode(client: httpx.AsyncClient, project_id: str) -> str:
    resp = await client.post(
        f"/api/v1/projects/{project_id}/episodes",
        json={"name": "Episode 1"},
    )
    return resp.json()["id"]


async def _create_folder(client: httpx.AsyncClient, project_id: str) -> str:
    resp = await client.post(
        f"/api/v1/projects/{project_id}/folders",
        json={"name": "Folder 1"},
    )
    return resp.json()["id"]


async def _create_project_location(client: httpx.AsyncClient, project_id: str) -> str:
    resp = await client.post(
        f"/api/v1/projects/{project_id}/locations",
        json={"address": "100 Test Location St"},
    )
    return resp.json()["id"]


# --- Scripted Location CRUD ---


async def test_create_scripted_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. DIVE BAR"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "INT. DIVE BAR"
    assert data["episode_id"] is None
    assert data["folder_id"] is None


async def test_create_scripted_location_with_episode(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    ep_id = await _create_episode(authenticated_client, proj_id)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "EXT. ROOFTOP", "episode_id": ep_id},
    )
    assert resp.status_code == 201
    assert resp.json()["episode_id"] == ep_id


async def test_create_scripted_location_with_folder(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    folder_id = await _create_folder(authenticated_client, proj_id)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. KITCHEN", "folder_id": folder_id},
    )
    assert resp.status_code == 201
    assert resp.json()["folder_id"] == folder_id


async def test_create_scripted_location_invalid_episode(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={
            "name": "INT. BAD",
            "episode_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert resp.status_code == 400


async def test_list_scripted_locations(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. OFFICE"},
    )
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "EXT. PARKING LOT"},
    )
    resp = await authenticated_client.get(
        f"/api/v1/projects/{proj_id}/scripted-locations"
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_scripted_locations_filter_by_episode(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    ep_id = await _create_episode(authenticated_client, proj_id)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. OFFICE"},
    )
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "EXT. PARK", "episode_id": ep_id},
    )
    resp = await authenticated_client.get(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        params={"episode_id": ep_id},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "EXT. PARK"


async def test_get_scripted_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. LOBBY"},
    )
    sl_id = create_resp.json()["id"]
    resp = await authenticated_client.get(
        f"/api/v1/projects/{proj_id}/scripted-locations/{sl_id}"
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "INT. LOBBY"


async def test_update_scripted_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. OLD NAME"},
    )
    sl_id = create_resp.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/projects/{proj_id}/scripted-locations/{sl_id}",
        json={"name": "INT. NEW NAME"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "INT. NEW NAME"


async def test_delete_scripted_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. TO DELETE"},
    )
    sl_id = create_resp.json()["id"]
    resp = await authenticated_client.delete(
        f"/api/v1/projects/{proj_id}/scripted-locations/{sl_id}"
    )
    assert resp.status_code == 204


# --- Scripted Location Locations ---


async def test_add_location_to_scripted_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    pl_id = await _create_project_location(authenticated_client, proj_id)
    sl_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. BAR"},
    )
    sl_id = sl_resp.json()["id"]
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations/{sl_id}/locations",
        json={"project_location_id": pl_id, "notes": "Great option"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["project_location_id"] == pl_id
    assert data["notes"] == "Great option"
    # Nested location info
    assert data["location"]["address"] == "100 Test Location St"
    assert data["location"]["id"] == pl_id
    # Nested user info
    assert "display_name" in data["added_by"]
    assert "id" in data["added_by"]


async def test_list_scripted_location_locations(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    pl_id = await _create_project_location(authenticated_client, proj_id)
    sl_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. BAR"},
    )
    sl_id = sl_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations/{sl_id}/locations",
        json={"project_location_id": pl_id},
    )
    resp = await authenticated_client.get(
        f"/api/v1/projects/{proj_id}/scripted-locations/{sl_id}/locations"
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["location"]["address"] == "100 Test Location St"
    assert "display_name" in items[0]["added_by"]


async def test_remove_location_from_scripted_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    pl_id = await _create_project_location(authenticated_client, proj_id)
    sl_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. BAR"},
    )
    sl_id = sl_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations/{sl_id}/locations",
        json={"project_location_id": pl_id},
    )
    resp = await authenticated_client.delete(
        f"/api/v1/projects/{proj_id}/scripted-locations/{sl_id}/locations/{pl_id}"
    )
    assert resp.status_code == 204


async def test_duplicate_location_in_scripted_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    pl_id = await _create_project_location(authenticated_client, proj_id)
    sl_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations",
        json={"name": "INT. BAR"},
    )
    sl_id = sl_resp.json()["id"]
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations/{sl_id}/locations",
        json={"project_location_id": pl_id},
    )
    dup_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/scripted-locations/{sl_id}/locations",
        json={"project_location_id": pl_id},
    )
    assert dup_resp.status_code == 409
