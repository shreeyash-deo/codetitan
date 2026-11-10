import json
import logging
import re
import time
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("brandshield.gemini")

# Mask known API key patterns to prevent accidental logging or exposure
KEY_REGEX = re.compile(r"AIzaSy[A-Za-z0-9_-]{33}")
URL_KEY_REGEX = re.compile(r"(key=)[A-Za-z0-9_-]+")


def redact_sensitive(text: str, api_key: str = "") -> str:
    """Ensure API keys and authorization headers are never logged or exposed in exceptions."""
    if not text:
        return ""
    redacted = str(text)
    if api_key and len(api_key) > 4:
        redacted = redacted.replace(api_key, "[REDACTED_API_KEY]")
    redacted = KEY_REGEX.sub("[REDACTED_API_KEY]", redacted)
    redacted = URL_KEY_REGEX.sub(r"\1[REDACTED_API_KEY]", redacted)
    return redacted


class GeminiError(Exception):
    """Base exception for all Gemini integration errors."""
    pass


class GeminiConfigurationError(GeminiError):
    """Raised when Gemini is selected but required configuration (e.g. API key) is missing."""
    pass


class GeminiAuthenticationError(GeminiError):
    """Raised when authentication fails due to an invalid or revoked API key (HTTP 401/403)."""
    pass


class GeminiModelError(GeminiError):
    """Raised when the configured model is unavailable, not found, or unsupported for the requested operation."""
    pass


class GeminiQuotaError(GeminiError):
    """Raised when API quota or billing limits are exhausted (HTTP 429 RESOURCE_EXHAUSTED)."""
    pass


class GeminiRateLimitError(GeminiError):
    """Raised when rate limits are exceeded after exhausting retries."""
    pass


class GeminiTimeoutError(GeminiError):
    """Raised when the API request times out."""
    pass


class GeminiNetworkError(GeminiError):
    """Raised on connection/network failures."""
    pass


class GeminiResponseError(GeminiError):
    """Raised when the API returns an unexpected or malformed payload."""
    pass


class GeminiClient:
    """
    Centralized client for Google Gemini Generative Language REST API (v1beta).
    Provides robust authentication, model selection, retry policies, error classification,
    and credential redaction.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self._explicit_key = api_key
        self._explicit_model = model
        self.temperature = temperature if temperature is not None else settings.AI_TEMPERATURE
        self.timeout = timeout if timeout is not None else settings.AI_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.AI_MAX_RETRIES

    @property
    def api_key(self) -> str:
        """
        Resolved API key.
        Precedence: Explicit argument > settings.GEMINI_API_KEY > settings.GOOGLE_API_KEY.
        """
        if self._explicit_key:
            return self._explicit_key.strip()
        return settings.active_gemini_api_key

    @property
    def model(self) -> str:
        """
        Resolved model identifier.
        Precedence: Explicit argument > settings.GEMINI_MODEL > settings.AI_MODEL > 'gemini-2.0-flash'.
        """
        if self._explicit_model:
            return self._explicit_model.strip()
        return settings.active_gemini_model

    def validate_configuration(self) -> None:
        """
        Verify that a valid API key is present when Gemini is used.
        Fails clearly without silently falling back to a different provider.
        """
        if not self.api_key:
            raise GeminiConfigurationError(
                "Gemini is configured as the AI provider, but no API key was found. "
                "Please set GEMINI_API_KEY (or GOOGLE_API_KEY) in backend/.env."
            )

    def _classify_http_error(self, status_code: int, response_text: str) -> GeminiError:
        """Classify HTTP error responses into specific Gemini exception categories with redacted text."""
        sanitized = redact_sensitive(response_text, self.api_key)

        error_status = ""
        error_message = sanitized
        try:
            parsed = json.loads(response_text)
            err_obj = parsed.get("error", {})
            error_status = err_obj.get("status", "")
            error_message = redact_sensitive(err_obj.get("message", sanitized), self.api_key)
        except Exception:
            pass

        lower_msg = error_message.lower()

        # 1. Authentication failure
        if status_code in (401, 403) or error_status == "API_KEY_INVALID" or "api key not valid" in lower_msg:
            return GeminiAuthenticationError(
                f"Gemini API authentication failed (HTTP {status_code}): Invalid or unauthenticated API key. "
                "Please verify GEMINI_API_KEY in backend/.env."
            )

        # 2. Model not found or unsupported
        if status_code == 404 or "not found for api version" in lower_msg or "not supported for generatecontent" in lower_msg:
            return GeminiModelError(
                f"Gemini model error: Configured model '{self.model}' is not available or does not support "
                f"generateContent on Google Generative Language API v1beta (HTTP {status_code}). "
                f"Details: {error_message}"
            )

        # 3. Quota vs Rate Limit
        if status_code == 429 or error_status == "RESOURCE_EXHAUSTED":
            if "quota" in lower_msg or "billing" in lower_msg:
                return GeminiQuotaError(
                    f"Gemini API quota exhausted or billing plan limit reached (HTTP 429): {error_message}"
                )
            return GeminiRateLimitError(
                f"Gemini API rate limit exceeded (HTTP 429): {error_message}"
            )

        # 4. General Bad Request or server error
        return GeminiError(
            f"Gemini API returned HTTP {status_code} ({error_status or 'ERROR'}): {error_message[:250]}"
        )

    def generate_content(
        self,
        prompt: str,
        system_instruction: str = "",
        response_mime_type: str = "application/json",
        temperature: Optional[float] = None,
    ) -> str:
        """
        Execute generateContent request against Google Generative Language API (v1beta).
        Applies retry policy for transient errors, redacts credentials, and extracts structured text.
        """
        self.validate_configuration()

        temp = temperature if temperature is not None else self.temperature
        url = f"{self.BASE_URL}/{self.model}:generateContent"

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temp,
            },
        }

        if response_mime_type:
            payload["generationConfig"]["response_mime_type"] = response_mime_type

        if system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction}]
            }

        retries = 0
        last_error: Optional[Exception] = None

        while retries <= self.max_retries:
            try:
                with httpx.Client(timeout=float(self.timeout)) as client:
                    resp = client.post(url, json=payload, headers=headers)

                if resp.status_code == 200:
                    resp_json = resp.json()
                    candidates = resp_json.get("candidates", [])
                    if not candidates:
                        block_reason = resp_json.get("promptFeedback", {}).get("blockReason")
                        if block_reason:
                            raise GeminiResponseError(f"Gemini API blocked the request. Reason: {block_reason}")
                        raise GeminiResponseError("Gemini API returned an empty candidates list in response.")

                    first_candidate = candidates[0]
                    finish_reason = first_candidate.get("finishReason")
                    if finish_reason in ("SAFETY", "RECITATION", "BLOCKLIST"):
                        raise GeminiResponseError(f"Gemini generation stopped prematurely due to {finish_reason}.")

                    parts = first_candidate.get("content", {}).get("parts", [])
                    if not parts or "text" not in parts[0]:
                        raise GeminiResponseError("Gemini response candidate does not contain text.")

                    return parts[0]["text"]

                # Non-200 response: classify error
                classified = self._classify_http_error(resp.status_code, resp.text)

                # Retry only transient errors (rate limit or server unavailable)
                if isinstance(classified, GeminiRateLimitError) or resp.status_code in (500, 502, 503, 504):
                    if retries < self.max_retries:
                        retries += 1
                        time.sleep(1.0 * retries)
                        continue

                raise classified

            except httpx.TimeoutException:
                last_error = GeminiTimeoutError(f"Gemini API request timed out after {self.timeout}s.")
                if retries < self.max_retries:
                    retries += 1
                    time.sleep(1.0 * retries)
                    continue
                raise last_error

            except httpx.RequestError as exc:
                last_error = GeminiNetworkError(f"Network error communicating with Gemini API: {redact_sensitive(str(exc))}")
                if retries < self.max_retries:
                    retries += 1
                    time.sleep(1.0 * retries)
                    continue
                raise last_error

        if last_error:
            raise last_error
        raise GeminiError("Gemini API request failed after exhausting retry attempts.")

    def check_health(self, probe_live: bool = False) -> Dict[str, Any]:
        """
        Lightweight backend diagnostic check.
        When probe_live=False, returns configuration status without consuming API quota.
        When probe_live=True, sends a minimal authenticated probe to verify end-to-end API readiness.
        """
        key_configured = bool(self.api_key)
        masked_hint = (
            f"...{self.api_key[-4:]}"
            if (self.api_key and len(self.api_key) >= 8)
            else ("configured" if key_configured else "none")
        )

        result: Dict[str, Any] = {
            "provider": "gemini",
            "api_key_configured": key_configured,
            "key_hint": masked_hint,
            "model": self.model,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "status": "ready" if key_configured else "missing_key",
        }

        if not probe_live:
            return result

        if not key_configured:
            result["status"] = "missing_api_key"
            result["error_category"] = "configuration"
            result["error"] = "GEMINI_API_KEY is not configured in backend/.env."
            return result

        # Perform minimal authenticated probe
        try:
            raw_resp = self.generate_content(
                prompt="Respond strictly with JSON: {\"status\": \"ok\"}",
                system_instruction="You are a health probe. Respond only with valid JSON.",
            )
            parsed = json.loads(raw_resp.strip())
            result["status"] = "healthy"
            result["verified"] = True
            result["probe_result"] = parsed
        except GeminiAuthenticationError as err:
            result["status"] = "invalid_api_key"
            result["error_category"] = "authentication"
            result["error"] = str(err)
        except GeminiModelError as err:
            result["status"] = "unsupported_model"
            result["error_category"] = "model"
            result["error"] = str(err)
        except GeminiQuotaError as err:
            result["status"] = "quota_exhausted"
            result["error_category"] = "quota"
            result["error"] = str(err)
        except GeminiRateLimitError as err:
            result["status"] = "rate_limited"
            result["error_category"] = "rate_limit"
            result["error"] = str(err)
        except GeminiTimeoutError as err:
            result["status"] = "timeout"
            result["error_category"] = "timeout"
            result["error"] = str(err)
        except GeminiResponseError as err:
            result["status"] = "malformed_response"
            result["error_category"] = "response"
            result["error"] = str(err)
        except Exception as err:
            result["status"] = "error"
            result["error_category"] = "unknown"
            result["error"] = redact_sensitive(str(err), self.api_key)

        return result


gemini_client = GeminiClient()
