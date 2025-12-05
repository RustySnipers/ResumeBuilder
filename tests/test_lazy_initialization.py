import importlib
import sys
import types

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient


PAYLOAD = {
    "job_description_text": "We need a Python developer with FastAPI experience",
    "resume_raw_text": "Software Engineer with Django and Flask experience",
}


def reload_main(monkeypatch: pytest.MonkeyPatch, lite_mode: bool, api_key: str | None):
    monkeypatch.setenv("LITE_MODE", "true" if lite_mode else "false")
    if api_key is None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ANTHROPIC_API_KEY", api_key)

    # Stub auth routers and missing database session module so imports do not fail
    auth_package = types.ModuleType("backend.auth")
    auth_package.__path__ = []  # type: ignore[attr-defined]
    sys.modules["backend.auth"] = auth_package

    auth_router_module = types.ModuleType("backend.auth.router")
    auth_router_module.router = APIRouter()
    sys.modules["backend.auth.router"] = auth_router_module

    api_key_router_module = types.ModuleType("backend.auth.api_key_router")
    api_key_router_module.router = APIRouter()
    sys.modules["backend.auth.api_key_router"] = api_key_router_module

    rate_limiter_module = types.ModuleType("backend.auth.rate_limiter")

    class _StubRateLimiter:  # pragma: no cover - stub for import wiring
        def __init__(self, *_, **__):
            self.redis_client = None

        async def connect(self):
            return None

        async def disconnect(self):
            return None

    rate_limiter_module.UserRateLimiter = _StubRateLimiter
    sys.modules["backend.auth.rate_limiter"] = rate_limiter_module

    dependencies_module = types.ModuleType("backend.auth.dependencies")

    async def _stub_dependency(*_, **__):  # pragma: no cover - stub for import wiring
        return None

    for name in [
        "get_current_active_user",
        "get_current_user",
        "check_account_lockout",
        "handle_failed_login",
        "handle_successful_login",
    ]:
        setattr(dependencies_module, name, _stub_dependency)

    sys.modules["backend.auth.dependencies"] = dependencies_module

    resume_router_module = types.ModuleType("backend.resumes.router")
    resume_router_module.router = APIRouter()
    sys.modules["backend.resumes.router"] = resume_router_module
    # Ensure package placeholder exists for resume imports
    resumes_package = types.ModuleType("backend.resumes")
    resumes_package.router = resume_router_module.router
    sys.modules["backend.resumes"] = resumes_package

    for module_name in [
        "backend.export.router",
        "backend.analytics.router",
        "backend.webhooks.router",
    ]:
        stub_module = types.ModuleType(module_name)
        stub_module.router = APIRouter()
        sys.modules[module_name] = stub_module

    session_module = types.ModuleType("backend.database.session")
    async def _get_session():  # pragma: no cover - stub for import wiring
        raise RuntimeError("Database session not available in tests")

    session_module.get_session = _get_session
    sys.modules["backend.database.session"] = session_module

    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    return importlib.reload(main)


class TestLazyInitialization:
    def test_standard_mode_only_initializes_nlp_on_use(self, monkeypatch: pytest.MonkeyPatch):
        main = reload_main(monkeypatch, lite_mode=False, api_key="test-key")

        # Stub NLP functions to avoid heavy dependencies while tracking initialization
        def _stub_redact(text: str) -> str:
            main.pii_detector = object()
            return text

        def _stub_gap(resume: str, job_description: str):
            main.semantic_analyzer = object()
            main.keyword_extractor = object()
            main.section_parser = object()
            return main.GapAnalysisResult(
                missing_keywords=[],
                suggestions=[],
                match_score=0.0,
                semantic_similarity=0.0,
            )

        monkeypatch.setattr(main, "redact_pii", _stub_redact)
        monkeypatch.setattr(main, "enhanced_gap_analysis", _stub_gap)

        # Nothing should be initialized before hitting endpoints
        assert main.pii_detector is None
        assert main.semantic_analyzer is None
        assert main.keyword_extractor is None
        assert main.section_parser is None
        assert main.llm_cache is None
        assert main.claude_client is None

        with TestClient(main.app) as client:
            response = client.post("/api/v1/analyze", json=PAYLOAD)

        assert response.status_code == 200
        assert main.pii_detector is not None
        assert main.semantic_analyzer is not None
        assert main.keyword_extractor is not None
        assert main.section_parser is not None
        # LLM components remain untouched until their routes are used
        assert main.llm_cache is None
        assert main.claude_client is None

        sys.modules.pop("main", None)

    def test_lite_mode_uses_stub_client(self, monkeypatch: pytest.MonkeyPatch):
        main = reload_main(monkeypatch, lite_mode=True, api_key=None)

        monkeypatch.setattr(main, "redact_pii", lambda text: text)

        def _stub_gap(resume: str, job_description: str):
            return main.GapAnalysisResult(
                missing_keywords=[],
                suggestions=[],
                match_score=0.0,
                semantic_similarity=0.0,
            )

        monkeypatch.setattr(main, "enhanced_gap_analysis", _stub_gap)

        with TestClient(main.app) as client:
            response = client.post("/api/v1/generate", json=PAYLOAD)

        assert response.status_code == 200
        assert main.claude_client is not None
        assert getattr(main.claude_client, "is_stub", False) is True

        sys.modules.pop("main", None)
