import httpx

from app.tasks.example import add, ping


def test_add_task() -> None:
    result = add(2, 3)
    assert result == 5


def test_ping_task() -> None:
    result = ping()
    assert result == "pong"


async def test_dispatch_ping_endpoint(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/v1/health/tasks/ping")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "dispatched"
    assert "task_id" in data
