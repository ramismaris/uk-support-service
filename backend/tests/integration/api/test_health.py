from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_health_no_auth_required(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
