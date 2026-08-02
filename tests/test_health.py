from fastapi.testclient import TestClient

from app.main import app


def _assert_health_payload(response):
    # 200 = healthy, 503 = postgres down (expected in CI where no real DB runs)
    assert response.status_code in (200, 503)
    payload = response.json()
    assert 'status' in payload
    assert payload['status'] in ('ok', 'degraded', 'error')
    assert 'checks' in payload
    assert 'mongo' in payload['checks']
    assert 'postgres' in payload['checks']


def test_health_endpoint_returns_payload():
    client = TestClient(app)
    _assert_health_payload(client.get('/health'))


def test_api_health_alias_returns_payload():
    """Vercel proxies browser health checks as /api/health."""
    client = TestClient(app)
    _assert_health_payload(client.get('/api/health'))
