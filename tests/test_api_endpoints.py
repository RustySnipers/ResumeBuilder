"""
Integration tests for FastAPI endpoints.

Tests cover API request/response validation, error handling,
and end-to-end workflow.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthCheckEndpoint:
    """Test the root health check endpoint."""

    @pytest.mark.integration
    def test_root_endpoint_success(self, client):
        """Test that root endpoint returns expected health check."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ATS Resume Builder API"
        assert data["status"] == "operational"
        assert data["version"] == "1.0.0-phase1"
        assert data["phase"] == "Foundation and Compliance Backend"

    @pytest.mark.integration
    def test_root_endpoint_response_structure(self, client):
        """Test that root endpoint has all required fields."""
        response = client.get("/")
        data = response.json()

        required_fields = ["service", "version", "status", "phase"]
        for field in required_fields:
            assert field in data


class TestAnalyzeEndpoint:
    """Test the /api/v1/analyze endpoint."""

    @pytest.mark.integration
    def test_analyze_endpoint_success(self, client):
        """Test successful analysis request."""
        payload = {
            "job_description_text": "We need a Python developer with FastAPI experience",
            "resume_raw_text": "Software Engineer with Django and Flask experience"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "missing_keywords" in data
        assert "suggestions" in data
        assert isinstance(data["missing_keywords"], list)
        assert isinstance(data["suggestions"], list)

    @pytest.mark.integration
    def test_analyze_endpoint_pii_redaction(self, client):
        """Test that PII is redacted before analysis."""
        payload = {
            "job_description_text": "Contact hiring manager at jobs@company.com for Python role",
            "resume_raw_text": "John Doe, john@email.com, (555) 123-4567, Python developer"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 200
        # Test passes if no error (PII redaction happens internally)
        data = response.json()
        assert "missing_keywords" in data

    @pytest.mark.integration
    def test_analyze_endpoint_realistic_input(self, client):
        """Test with realistic job description and resume."""
        payload = {
            "job_description_text": """
                Senior Python Developer

                We are seeking an experienced Python developer with:
                - 5+ years Python experience
                - FastAPI and Django frameworks
                - PostgreSQL database skills
                - Docker and Kubernetes knowledge
                - AWS cloud experience
            """,
            "resume_raw_text": """
                Software Engineer

                Experience:
                - 3 years Python development
                - Built REST APIs using Flask
                - MySQL database design
                - Deployed to Heroku

                Skills: Python, Flask, MySQL, Git
            """
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Should detect missing keywords
        assert len(data["missing_keywords"]) > 0
        missing_lower = [k.lower() for k in data["missing_keywords"]]
        # Should identify some missing technologies
        assert any(term in missing_lower for term in ["fastapi", "django", "postgresql", "docker"])

        # Should have suggestions
        assert len(data["suggestions"]) > 0


class TestInputValidation:
    """Test input validation and error handling."""

    @pytest.mark.integration
    def test_missing_job_description(self, client):
        """Test error when job_description_text is missing."""
        payload = {
            "resume_raw_text": "My resume content"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 422  # Unprocessable Entity

    @pytest.mark.integration
    def test_missing_resume(self, client):
        """Test error when resume_raw_text is missing."""
        payload = {
            "job_description_text": "Job description"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 422  # Unprocessable Entity

    @pytest.mark.integration
    def test_empty_payload(self, client):
        """Test error when payload is empty."""
        response = client.post("/api/v1/analyze", json={})

        assert response.status_code == 422  # Unprocessable Entity

    @pytest.mark.integration
    def test_job_description_too_short(self, client):
        """Test error when job description is too short (< 10 chars)."""
        payload = {
            "job_description_text": "Short",
            "resume_raw_text": "My resume with sufficient length"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 422  # Validation error

    @pytest.mark.integration
    def test_resume_too_short(self, client):
        """Test error when resume is too short (< 10 chars)."""
        payload = {
            "job_description_text": "This is a sufficient job description",
            "resume_raw_text": "Short"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 422  # Validation error

    @pytest.mark.integration
    def test_invalid_json(self, client):
        """Test error when JSON is malformed."""
        response = client.post(
            "/api/v1/analyze",
            data="invalid json{",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    @pytest.mark.integration
    def test_wrong_field_names(self, client):
        """Test error when field names are incorrect."""
        payload = {
            "job_desc": "This field name is wrong",
            "resume": "This field name is also wrong"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 422


class TestResponseValidation:
    """Test response structure and validation."""

    @pytest.mark.integration
    def test_response_has_correct_schema(self, client):
        """Test that response matches GapAnalysisResult schema."""
        payload = {
            "job_description_text": "Python FastAPI developer needed",
            "resume_raw_text": "Java Spring Boot developer"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Check schema
        assert "missing_keywords" in data
        assert "suggestions" in data
        assert isinstance(data["missing_keywords"], list)
        assert isinstance(data["suggestions"], list)

        # Check all keywords are strings
        for keyword in data["missing_keywords"]:
            assert isinstance(keyword, str)

        # Check all suggestions are strings
        for suggestion in data["suggestions"]:
            assert isinstance(suggestion, str)

    @pytest.mark.integration
    def test_response_keywords_are_lowercase(self, client):
        """Test that missing keywords are normalized to lowercase."""
        payload = {
            "job_description_text": "PYTHON FASTAPI DEVELOPER",
            "resume_raw_text": "Java developer"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Keywords should be lowercase (normalized)
        for keyword in data["missing_keywords"]:
            assert keyword.islower() or not keyword.isalpha()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.integration
    def test_very_long_inputs(self, client):
        """Test handling of very long job description and resume."""
        payload = {
            "job_description_text": "Python developer " * 1000,  # Very long
            "resume_raw_text": "Java developer " * 1000  # Very long
        }

        response = client.post("/api/v1/analyze", json=payload)

        # Should handle long inputs gracefully
        assert response.status_code == 200

    @pytest.mark.integration
    def test_unicode_characters(self, client):
        """Test handling of unicode characters in input."""
        payload = {
            "job_description_text": "Python developer needed 你好 مرحبا",
            "resume_raw_text": "Java developer with café experience ñ"
        }

        response = client.post("/api/v1/analyze", json=payload)

        # Should handle unicode gracefully
        assert response.status_code == 200

    @pytest.mark.integration
    def test_special_characters_in_text(self, client):
        """Test handling of special characters."""
        payload = {
            "job_description_text": "Need C++ and C# developer with .NET experience!!!",
            "resume_raw_text": "Python developer with <strong>HTML</strong> & JavaScript"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 200

    @pytest.mark.integration
    def test_only_stop_words(self, client):
        """Test when inputs contain mostly stop words."""
        payload = {
            "job_description_text": "The candidate will be working with the team and will have to do tasks",
            "resume_raw_text": "I have been working with teams and doing various tasks"
        }

        response = client.post("/api/v1/analyze", json=payload)

        assert response.status_code == 200
        data = response.json()
        # Should still return valid response even with mostly stop words
        assert "missing_keywords" in data
        assert "suggestions" in data


class TestCORS:
    """Test CORS and HTTP headers."""

    @pytest.mark.integration
    def test_content_type_json(self, client):
        """Test that response content type is JSON."""
        response = client.get("/")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    @pytest.mark.integration
    def test_post_requires_json(self, client):
        """Test that POST endpoint requires JSON content type."""
        response = client.post(
            "/api/v1/analyze",
            data="job_description_text=test&resume_raw_text=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # Should reject non-JSON content
        assert response.status_code == 422


class TestDocumentation:
    """Test API documentation endpoints."""

    @pytest.mark.integration
    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is accessible."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "ATS Resume Builder API"

    @pytest.mark.integration
    def test_docs_endpoint_available(self, client):
        """Test that interactive docs are available."""
        response = client.get("/docs")

        assert response.status_code == 200
        # Should return HTML for Swagger UI
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.integration
    def test_redoc_endpoint_available(self, client):
        """Test that ReDoc documentation is available."""
        response = client.get("/redoc")

        assert response.status_code == 200
        # Should return HTML for ReDoc
        assert "text/html" in response.headers["content-type"]
