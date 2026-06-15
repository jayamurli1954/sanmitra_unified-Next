from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_payload():
    client = TestClient(app)
    response = client.get('/health')
    # 200 = healthy, 503 = postgres down (expected in CI where no real DB runs)
    assert response.status_code in (200, 503)
    payload = response.json()
    assert 'status' in payload
    assert payload['status'] in ('ok', 'degraded', 'error')
    assert 'checks' in payload
    assert 'mongo' in payload['checks']
    assert 'postgres' in payload['checks']
