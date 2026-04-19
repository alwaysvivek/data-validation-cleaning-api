"""Tests for the /ai/* endpoints."""

import io
from unittest.mock import patch, MagicMock

import pandas as pd


class TestAIEndpointsNoKey:
    """When GROQ_API_KEY is not set, AI endpoints should return 503."""

    def test_analyze_suggest_returns_503(self, client):
        resp = client.post(
            "/api/v1/ai/analyze",
            json={"action": "suggest", "data": [{"a": 1}]},
        )
        assert resp.status_code == 503
        assert resp.json()["error"] == "AI_SERVICE_UNAVAILABLE"

    def test_analyze_standardize_returns_503(self, client):
        resp = client.post(
            "/api/v1/ai/analyze",
            json={"action": "standardize", "values": ["NY", "New York", "new york"]},
        )
        assert resp.status_code == 503

    def test_analyze_profile_returns_503(self, client):
        resp = client.post(
            "/api/v1/ai/analyze",
            json={"action": "profile", "data": [{"a": 1}]},
        )
        assert resp.status_code == 503


class TestAIEndpointsMocked:
    """Test AI endpoints with mocked Groq responses."""

    @patch("app.services.ai_service.settings")
    @patch("app.services.ai_service.GroqAIService._chat")
    def test_analyze_suggest_returns_suggestions(self, mock_chat, mock_settings, client):
        mock_settings.groq_available = True
        mock_settings.GROQ_API_KEY = "test-key"
        mock_settings.GROQ_MODEL = "test-model"

        mock_chat.return_value = (
            '[{"column": "age", "issue": "nulls", "suggestion": "fill with median", "confidence": 0.9}]'
        )

        resp = client.post(
            "/api/v1/ai/analyze",
            json={"action": "suggest", "data": [{"age": 30}, {"age": None}]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 1
        assert body[0]["column"] == "age"

    @patch("app.services.ai_service.settings")
    @patch("app.services.ai_service.GroqAIService._chat")
    def test_analyze_standardize_returns_mapping(self, mock_chat, mock_settings, client):
        mock_settings.groq_available = True
        mock_settings.GROQ_API_KEY = "test-key"
        mock_settings.GROQ_MODEL = "test-model"

        mock_chat.return_value = (
            '{"standardized_values": ["New York", "New York", "New York"], '
            '"mapping": {"NY": "New York", "new york": "New York"}}'
        )

        resp = client.post(
            "/api/v1/ai/analyze",
            json={"action": "standardize", "values": ["NY", "New York", "new york"], "context": "US states"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "mapping" in body
        assert body["mapping"]["NY"] == "New York"
        
    @patch("app.services.ai_service.settings")
    @patch("app.services.ai_service.GroqAIService._chat")
    def test_analyze_profile_returns_summary(self, mock_chat, mock_settings, client):
        mock_settings.groq_available = True
        mock_settings.GROQ_API_KEY = "test-key"
        mock_settings.GROQ_MODEL = "test-model"

        mock_chat.return_value = "This is a great dataset with some missing values."

        resp = client.post(
            "/api/v1/ai/analyze",
            json={"action": "profile", "data": [{"age": 30}, {"age": None}]},
        )
        assert resp.status_code == 200
        assert resp.json() == "This is a great dataset with some missing values."

    @patch("app.services.ai_service.settings")
    def test_analyze_missing_data_returns_400(self, mock_settings, client):
        mock_settings.groq_available = True
        mock_settings.GROQ_API_KEY = "test-key"
        resp = client.post(
            "/api/v1/ai/analyze",
            json={"action": "suggest"} # missing data
        )
        assert resp.status_code == 400

    @patch("app.services.ai_service.settings")
    def test_analyze_missing_values_returns_400(self, mock_settings, client):
        mock_settings.groq_available = True
        mock_settings.GROQ_API_KEY = "test-key"
        resp = client.post(
            "/api/v1/ai/analyze",
            json={"action": "standardize"} # missing values
        )
        assert resp.status_code == 400
