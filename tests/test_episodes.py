import httpx


async def _create_project(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/projects", json={"name": "EP Project", "project_type": "tv_show"}
    )
    return resp.json()["id"]


async def test_create_episode(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/episodes",
        json={"name": "Pilot", "description": "First episode", "sort_order": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Pilot"
    assert data["sort_order"] == 1
    assert data["project_id"] == proj_id


async def test_list_episodes(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/episodes",
        json={"name": "Ep 1", "sort_order": 1},
    )
    await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/episodes",
        json={"name": "Ep 2", "sort_order": 2},
    )
    resp = await authenticated_client.get(f"/api/v1/projects/{proj_id}/episodes")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_episode(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/episodes",
        json={"name": "Detail Ep"},
    )
    ep_id = create_resp.json()["id"]
    resp = await authenticated_client.get(
        f"/api/v1/projects/{proj_id}/episodes/{ep_id}"
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Detail Ep"


async def test_update_episode(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/episodes",
        json={"name": "Old Ep"},
    )
    ep_id = create_resp.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/projects/{proj_id}/episodes/{ep_id}",
        json={"name": "New Ep", "sort_order": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Ep"
    assert resp.json()["sort_order"] == 5


async def test_delete_episode(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj_id = await _create_project(authenticated_client)
    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj_id}/episodes",
        json={"name": "To Delete"},
    )
    ep_id = create_resp.json()["id"]
    resp = await authenticated_client.delete(
        f"/api/v1/projects/{proj_id}/episodes/{ep_id}"
    )
    assert resp.status_code == 204


async def test_episode_cross_project_denied(
    authenticated_client: httpx.AsyncClient,
) -> None:
    proj1_id = await _create_project(authenticated_client)
    proj2_resp = await authenticated_client.post(
        "/api/v1/projects", json={"name": "Other Project", "project_type": "movie"}
    )
    proj2_id = proj2_resp.json()["id"]

    create_resp = await authenticated_client.post(
        f"/api/v1/projects/{proj1_id}/episodes",
        json={"name": "Ep in Proj1"},
    )
    ep_id = create_resp.json()["id"]

    resp = await authenticated_client.get(
        f"/api/v1/projects/{proj2_id}/episodes/{ep_id}"
    )
    assert resp.status_code == 404
