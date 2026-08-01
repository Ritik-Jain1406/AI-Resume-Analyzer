"""
ai/gemini_service.py
------------------------
Dedicated service boundary for all Google Gemini API interactions
(Phase 7). No other module should import the google.genai SDK directly.

Security/privacy guarantees this module upholds:
- The API key is read only from config.settings.gemini_api_key, which is
  itself populated only from the GEMINI_API_KEY environment variable /
  .env file (see config.py). It is never hardcoded, never returned from
  any function here, and never included in a log line or exception
  message.
- All SDK exceptions are caught and translated into one of the
  GeminiServiceError subclasses below with a short, safe, user-facing
  message. Callers (ai/recommendation.py, app.py) can show
  `str(exc)` directly without risking leaking request/response internals
  or the key itself.
- The client is created lazily on first use, so importing this module —
  and running the test suite — never requires a configured key or
  network access.
"""

from __future__ import annotations

import json

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_client = None  # lazily initialized, cached Gemini client


class GeminiServiceError(Exception):
    """Base class for all Gemini-related errors. Message is always safe to show the user."""


class GeminiConfigError(GeminiServiceError):
    """Missing/invalid API key, missing SDK, or bad model configuration."""


class GeminiAPIError(GeminiServiceError):
    """Network failure, timeout, rate limiting, or a server-side API error."""


class GeminiResponseError(GeminiServiceError):
    """The model's response was empty, not valid JSON, or failed schema validation."""


def _get_client():
    """Lazily construct and cache the Gemini client. Raises GeminiConfigError if unavailable."""
    global _client
    if _client is not None:
        return _client

    api_key = settings.gemini_api_key
    if not api_key or not api_key.strip():
        raise GeminiConfigError(
            "Gemini API key is not configured. Add GEMINI_API_KEY to your local .env file."
        )

    try:
        from google import genai
    except ImportError as exc:
        raise GeminiConfigError(
            "The google-genai package isn't installed. Run: pip install -r requirements.txt"
        ) from exc

    try:
        _client = genai.Client(api_key=api_key)
    except Exception as exc:  # noqa: BLE001 - never let a raw SDK exception (or the key) escape
        logger.error("Failed to initialize Gemini client ({})", type(exc).__name__)
        raise GeminiConfigError(
            "Could not initialize the Gemini client. Check that GEMINI_API_KEY is valid."
        ) from exc

    return _client


def is_configured() -> bool:
    """Whether a Gemini API key is present, without attempting to connect."""
    return bool(settings.gemini_api_key and settings.gemini_api_key.strip())


def generate_json(system_instruction: str, prompt: str) -> dict:
    """
    Send `prompt` to Gemini (with `system_instruction`) requesting a JSON
    response, and return the parsed dict.

    Never raises a raw SDK exception — only GeminiConfigError,
    GeminiAPIError, or GeminiResponseError, each with a message that's
    already safe to display to the user.
    """
    client = _get_client()

    try:
        from google.genai import types
        from google.genai import errors as genai_errors
    except ImportError as exc:
        raise GeminiConfigError(
            "The google-genai package isn't installed. Run: pip install -r requirements.txt"
        ) from exc

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
            ),
        )
    except genai_errors.APIError as exc:
        code = getattr(exc, "code", None)
        logger.error("Gemini API error (code={})", code)
        if code == 429:
            raise GeminiAPIError(
                "Gemini API rate limit reached. Please wait a moment and try again."
            ) from exc
        if code in (401, 403):
            raise GeminiConfigError(
                "Gemini API key was rejected. Check that GEMINI_API_KEY is valid."
            ) from exc
        if code == 404:
            raise GeminiConfigError(
                "The configured Gemini model was not found. Check the GEMINI_MODEL setting."
            ) from exc
        if isinstance(code, int) and code >= 500:
            raise GeminiAPIError(
                "Gemini's service is temporarily unavailable. Please try again shortly."
            ) from exc
        raise GeminiAPIError("The Gemini API request failed. Please try again.") from exc
    except Exception as exc:  # noqa: BLE001 - network errors/timeouts aren't always APIError
        logger.error("Unexpected error calling Gemini ({})", type(exc).__name__)
        raise GeminiAPIError(
            "Could not reach the Gemini API (network issue or timeout). Please try again."
        ) from exc

    text = getattr(response, "text", None)
    if not text or not text.strip():
        raise GeminiResponseError("Gemini returned an empty response. Please try again.")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("Gemini response was not valid JSON ({} chars received)", len(text))
        raise GeminiResponseError(
            "Gemini's response could not be parsed. Please try regenerating."
        ) from exc
