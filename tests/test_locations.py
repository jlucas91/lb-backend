import httpx


async def test_create_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    resp = await authenticated_client.post(
        "/api/v1/locations",
        json={"address": "123 Main St, LA", "city": "LA", "location_type": "studio"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["address"] == "123 Main St, LA"
    assert data["city"] == "LA"
    assert data["location_type"] == "studio"


async def test_list_locations(
    authenticated_client: httpx.AsyncClient,
) -> None:
    await authenticated_client.post("/api/v1/locations", json={"address": "100 Elm St"})
    await authenticated_client.post(
        "/api/v1/locations", json={"address": "200 Oak Ave"}
    )
    resp = await authenticated_client.get("/api/v1/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_get_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "456 Detail Ln"}
    )
    loc_id = create_resp.json()["id"]
    resp = await authenticated_client.get(f"/api/v1/locations/{loc_id}")
    assert resp.status_code == 200
    assert resp.json()["address"] == "456 Detail Ln"


async def test_update_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "Old Address"}
    )
    loc_id = create_resp.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/locations/{loc_id}", json={"address": "New Address"}
    )
    assert resp.status_code == 200
    assert resp.json()["address"] == "New Address"


async def test_delete_location(
    authenticated_client: httpx.AsyncClient,
) -> None:
    create_resp = await authenticated_client.post(
        "/api/v1/locations", json={"address": "789 Delete Rd"}
    )
    loc_id = create_resp.json()["id"]
    resp = await authenticated_client.delete(f"/api/v1/locations/{loc_id}")
    assert resp.status_code == 204
    get_resp = await authenticated_client.get(f"/api/v1/locations/{loc_id}")
    assert get_resp.status_code == 404


async def test_filter_by_type(
    authenticated_client: httpx.AsyncClient,
) -> None:
    await authenticated_client.post(
        "/api/v1/locations",
        json={"address": "1 Studio Way", "location_type": "studio"},
    )
    await authenticated_client.post(
        "/api/v1/locations",
        json={"address": "2 Park Blvd", "location_type": "outdoor"},
    )
    resp = await authenticated_client.get(
        "/api/v1/locations", params={"location_type": "studio"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["location_type"] == "studio"


async def test_search_locations(
    authenticated_client: httpx.AsyncClient,
) -> None:
    await authenticated_client.post(
        "/api/v1/locations", json={"address": "Sunset Beach House, Malibu"}
    )
    await authenticated_client.post(
        "/api/v1/locations", json={"address": "Downtown Loft, DTLA"}
    )
    resp = await authenticated_client.get("/api/v1/locations", params={"q": "sunset"})
    data = resp.json()
    assert data["total"] == 1
    assert "Sunset" in data["items"][0]["address"]


async def test_pagination(
    authenticated_client: httpx.AsyncClient,
) -> None:
    for i in range(5):
        await authenticated_client.post(
            "/api/v1/locations", json={"address": f"{i} Test St"}
        )
    resp = await authenticated_client.get(
        "/api/v1/locations", params={"page": 1, "per_page": 2}
    )
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["pages"] == 3


async def test_unauthorized_access(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/locations")
    assert resp.status_code == 401
