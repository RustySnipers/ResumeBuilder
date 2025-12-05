import importlib
import sys

from fastapi.testclient import TestClient

from tests.test_lazy_initialization import PAYLOAD, reload_main


def test_lite_mode_generate_returns_canned_response(monkeypatch):
    main = reload_main(monkeypatch, lite_mode=True, api_key=None)

    monkeypatch.setattr(main, "redact_pii", lambda text: text)

    def _stub_gap(resume: str, job_description: str):
        return main.GapAnalysisResult(
            missing_keywords=["fastapi", "docker"],
            suggestions=["Add API metrics", "Mention containerization"],
            match_score=82.5,
            semantic_similarity=0.75,
        )

    monkeypatch.setattr(main, "enhanced_gap_analysis", _stub_gap)

    with TestClient(main.app) as client:
        response = client.post("/api/v1/generate", json=PAYLOAD)
        stream_response = client.post("/api/v1/generate/stream", json=PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert "Jane Doe" in data["optimized_resume"]
    assert data["usage_stats"]["model"] == "stub-claude-lite"

    assert stream_response.status_code == 200
    assert "Jane Doe" in stream_response.text

    # Ensure later imports see a clean module state
    sys.modules.pop("main", None)
    importlib.invalidate_caches()
