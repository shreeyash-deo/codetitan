import json
import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.core.config import settings
from app.models.rule import BrandRule
from app.services.ai.gemini_client import (
    GeminiClient,
    GeminiError,
    GeminiConfigurationError,
    GeminiAuthenticationError,
    GeminiModelError,
    GeminiQuotaError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiNetworkError,
    redact_sensitive,
)
from app.services.ai.gemini_provider import GeminiProvider
from app.services.compliance.ai_checker import ai_checker


def test_gemini_missing_api_key_raises_configuration_error():
    client = GeminiClient(api_key="")
    with patch.object(settings, "GEMINI_API_KEY", ""):
        with patch.object(settings, "GOOGLE_API_KEY", ""):
            with pytest.raises(GeminiConfigurationError) as exc_info:
                client.generate_content("hello")
            assert "no API key was found" in str(exc_info.value)
            assert "GEMINI_API_KEY" in str(exc_info.value)


def test_gemini_configuration_precedence():
    # 1. GEMINI_API_KEY takes precedence over GOOGLE_API_KEY
    with patch.object(settings, "GEMINI_API_KEY", "primary-gemini-key"):
        with patch.object(settings, "GOOGLE_API_KEY", "secondary-google-key"):
            client = GeminiClient()
            assert client.api_key == "primary-gemini-key"

    # 2. GOOGLE_API_KEY used if GEMINI_API_KEY is empty
    with patch.object(settings, "GEMINI_API_KEY", ""):
        with patch.object(settings, "GOOGLE_API_KEY", "secondary-google-key"):
            client = GeminiClient()
            assert client.api_key == "secondary-google-key"

    # 3. GEMINI_MODEL takes precedence over AI_MODEL
    with patch.object(settings, "GEMINI_MODEL", "gemini-custom-model"):
        with patch.object(settings, "AI_MODEL", "legacy-model"):
            client = GeminiClient()
            assert client.model == "gemini-custom-model"

    # 4. Default model fallback
    with patch.object(settings, "GEMINI_MODEL", ""):
        with patch.object(settings, "AI_MODEL", ""):
            client = GeminiClient()
            assert client.model == "gemini-2.0-flash"


def test_gemini_invalid_credentials_categorization():
    client = GeminiClient(api_key="AIzaSyFAKEKEYFORTESTING1234567890123")
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = json.dumps({
        "error": {
            "code": 400,
            "message": "API key not valid. Please pass a valid API key.",
            "status": "INVALID_ARGUMENT",
            "details": [{"reason": "API_KEY_INVALID"}]
        }
    })

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(GeminiAuthenticationError) as exc_info:
            client.generate_content("test prompt")
        assert "Invalid or unauthenticated API key" in str(exc_info.value)
        # Verify raw API key is never leaked
        assert "AIzaSyFAKEKEYFORTESTING1234567890123" not in str(exc_info.value)


def test_gemini_unsupported_model_categorization():
    client = GeminiClient(api_key="valid-mock-key", model="gemini-nonexistent-model")
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = json.dumps({
        "error": {
            "code": 404,
            "message": "models/gemini-nonexistent-model is not found for api version v1beta",
            "status": "NOT_FOUND"
        }
    })

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(GeminiModelError) as exc_info:
            client.generate_content("test prompt")
        assert "gemini-nonexistent-model" in str(exc_info.value)
        assert "not available or does not support generateContent" in str(exc_info.value)


def test_gemini_quota_exhaustion_categorization():
    client = GeminiClient(api_key="valid-mock-key")
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = json.dumps({
        "error": {
            "code": 429,
            "message": "Quota exceeded for quota metric 'Generate Content API requests' per minute",
            "status": "RESOURCE_EXHAUSTED"
        }
    })

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(GeminiQuotaError) as exc_info:
            client.generate_content("test prompt")
        assert "quota exhausted or billing plan limit reached" in str(exc_info.value).lower()


def test_gemini_rate_limit_and_retry_exhaustion():
    client = GeminiClient(api_key="valid-mock-key", max_retries=1)
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = json.dumps({
        "error": {
            "code": 429,
            "message": "Too many requests. Rate limit reached.",
            "status": "RESOURCE_EXHAUSTED"
        }
    })

    call_count = 0
    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp

    with patch("httpx.Client.post", side_effect=mock_post):
        with patch("time.sleep", return_value=None):
            with pytest.raises(GeminiRateLimitError):
                client.generate_content("test prompt")
            # max_retries=1 means 1 initial call + 1 retry = 2 calls
            assert call_count == 2


def test_gemini_timeout_handling():
    client = GeminiClient(api_key="valid-mock-key", timeout=10, max_retries=0)
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")):
        with pytest.raises(GeminiTimeoutError) as exc_info:
            client.generate_content("test prompt")
        assert "timed out after 10s" in str(exc_info.value)


def test_gemini_structured_rule_extraction():
    provider = GeminiProvider(api_key="valid-key", model="gemini-2.0-flash")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "rules": [
                                    {
                                        "title": "Always State Full Company Name",
                                        "description": "Never abbreviate NovaPay as NP.",
                                        "category": "Brand voice and tone",
                                        "source_reference": "Section 1.2",
                                        "confidence": 0.98,
                                    }
                                ]
                            })
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        candidates = provider.extract_rules("Always state the full company name.")
        assert len(candidates) == 1
        assert candidates[0].title == "Always State Full Company Name"
        assert candidates[0].category == "Brand voice and tone"


def test_ai_checker_grounding_rejects_hallucinated_rules():
    approved_rule = BrandRule(
        id=42,
        workspace_id=1,
        title="Prohibit Unverified Guarantees",
        description="Never use guaranteed returns.",
        category="Claims and disclaimers",
        approval_status="approved",
    )

    # Gemini returns two findings: one citing legitimate Rule #42, one citing fake Rule #999
    gemini_payload = {
        "summary": "Compliance analysis summary",
        "findings": [
            {
                "severity": "critical",
                "category": "Claims and disclaimers",
                "excerpt": "guaranteed returns",
                "explanation": "Violates no-guarantee policy",
                "guideline_reference": "Rule #42: Prohibit Unverified Guarantees",
                "confidence": 0.95,
            },
            {
                "severity": "major",
                "category": "Brand voice and tone",
                "excerpt": "instant results",
                "explanation": "Hallucinated rule reference",
                "guideline_reference": "Rule #999: Nonexistent Hallucinated Rule",
                "confidence": 0.90,
            },
        ],
    }

    with patch.object(settings, "GEMINI_API_KEY", "active-key"):
        with patch.object(settings, "AI_PROVIDER", "gemini"):
            with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(gemini_payload)):
                summary, findings = ai_checker.evaluate(
                    content="We offer guaranteed returns and instant results.",
                    content_type="blog",
                    approved_rules=[approved_rule],
                )

                # Finding for Rule #42 is preserved; fake Rule #999 is discarded!
                assert len(findings) == 1
                assert findings[0].guideline_reference == "Rule #42: Prohibit Unverified Guarantees"
                assert findings[0].excerpt == "guaranteed returns"


def test_ai_checker_deterministic_fallback_when_gemini_unavailable():
    approved_rule = BrandRule(
        id=1,
        workspace_id=1,
        title="Prohibit Unverified Terms",
        description="Do not say unverified.",
        category="Restricted terminology",
        approval_status="approved",
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock-key"):
        with patch.object(settings, "AI_PROVIDER", "gemini"):
            with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", side_effect=GeminiTimeoutError("Request timed out after 45s")):
                summary, findings = ai_checker.evaluate(
                    content="This is unverified copy.",
                    content_type="marketing",
                    approved_rules=[approved_rule],
                )
                assert "AI semantic analysis unavailable" in summary
                assert findings == []  # Deterministic checks run independently in ComplianceEngine


def test_credential_redaction_utility():
    secret_key = "AIzaSyABC123456789012345678901234567"
    raw_error = f"Error calling url with key={secret_key} and header x-goog-api-key: {secret_key}"
    sanitized = redact_sensitive(raw_error, secret_key)

    assert secret_key not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_health_ai_diagnostics_endpoint(client):
    # 1. Default without probe (no API quota consumed)
    with patch.object(settings, "GEMINI_API_KEY", ""):
        with patch.object(settings, "GOOGLE_API_KEY", ""):
            res = client.get("/health/ai")
            assert res.status_code == 200
            data = res.json()
            assert data["provider"] == "gemini"
            assert data["api_key_configured"] is False
            assert data["status"] == "missing_key"

    # 2. Live probe with mock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "{\"status\": \"ok\"}"}]
                }
            }
        ]
    }

    with patch.object(settings, "GEMINI_API_KEY", "valid-test-key"):
        with patch("httpx.Client.post", return_value=mock_resp):
            res_probe = client.get("/health/ai?probe=true")
            assert res_probe.status_code == 200
            probe_data = res_probe.json()
            assert probe_data["status"] == "healthy"
            assert probe_data["verified"] is True
            assert probe_data["api_key_configured"] is True
            # Confirm raw key is never exposed
            assert "valid-test-key" not in json.dumps(probe_data)
