import backend.database as database
from fastapi.testclient import TestClient

from tests.test_lazy_initialization import reload_main


def test_readiness_in_lite_mode_returns_ready_without_db(monkeypatch):
    """Readiness should return ready in lite mode without touching the database."""
    main = reload_main(monkeypatch, lite_mode=True, api_key=None)

    def _fail_check():  # pragma: no cover - should be skipped entirely
        raise AssertionError("check_db_health should not be called in lite mode")

    monkeypatch.setattr(database, "check_db_health", _fail_check)

    with TestClient(main.app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["lite_mode"] is True
    assert payload.get("degraded") is True
    assert "external services" in payload.get("message", "").lower()
