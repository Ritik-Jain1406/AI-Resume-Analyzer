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
import re

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_client = None  # lazily initialized, cached Gemini client

# Appended to the user prompt on the single automatic retry when Gemini's
# first response couldn't be parsed as JSON even after cleanup — a
# stronger, explicit reminder of the format requirement.
_RETRY_INSTRUCTION = (
    "\n\nIMPORTANT: Your previous response could not be parsed as JSON. "
    "Return ONLY valid JSON. Do not include markdown. Do not include "
    "explanations. Do not include code fences. Return exactly one JSON object."
)

_MARKDOWN_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class GeminiServiceError(Exception):
    """Base class for all Gemini-related errors. Message is always safe to show the user."""


class GeminiConfigError(GeminiServiceError):
    """Missing/invalid API key, missing SDK, or bad model configuration."""


class GeminiAPIError(GeminiServiceError):
    """Network failure, timeout, rate limiting, or a server-side API error."""


class GeminiResponseError(GeminiServiceError):
    """The model's response was empty, not valid JSON, or failed schema validation."""


class _JsonRecoveryFailed(Exception):
    """Internal signal only — never escapes this module. See _parse_gemini_json."""


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


def _strip_markdown_fences(text: str) -> str:
    """Remove a leading ```json / ``` fence and a trailing ``` fence, if present."""
    stripped = text.strip()
    stripped = _MARKDOWN_FENCE_RE.sub("", stripped)
    return stripped.strip()


def _extract_largest_json_object(text: str) -> str | None:
    """
    Scan `text` for balanced top-level {...} substrings (handling nested
    braces) and return the largest one found, or None if there isn't one.
    Used to recover a JSON object embedded in explanatory prose, e.g.:

        "Sure, here's the analysis:\n\n{...}\n\nLet me know if you need more."
    """
    best: str | None = None
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    candidate = text[start : i + 1]
                    if best is None or len(candidate) > len(best):
                        best = candidate
    return best


def _parse_gemini_json(text: str) -> dict:
    """
    Multi-step recovery parse of a Gemini text response into a dict:
      1. Parse as-is.
      2. Strip markdown code fences, parse again.
      3. Extract the largest {...} block from the (fence-stripped) text, parse that.

    Raises _JsonRecoveryFailed (an internal signal, never exposed outside
    this module) if all three steps fail — the caller decides whether to
    retry against the API or raise GeminiResponseError.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    logger.info("Gemini JSON parse failed on first attempt; attempting recovery")

    cleaned = _strip_markdown_fences(text)
    if cleaned != text.strip():
        try:
            parsed = json.loads(cleaned)
            logger.info("Gemini JSON recovered after stripping markdown fences")
            return parsed
        except json.JSONDecodeError:
            logger.info("Gemini JSON parse failed after stripping markdown fences")

    extracted = _extract_largest_json_object(cleaned)
    if extracted:
        try:
            parsed = json.loads(extracted)
            logger.info("Gemini JSON recovered by extracting a JSON object from surrounding text")
            return parsed
        except json.JSONDecodeError:
            logger.info("Gemini JSON parse failed even after extracting a JSON object")

    raise _JsonRecoveryFailed()


def _call_gemini(client, types, genai_errors, system_instruction: str, prompt: str) -> str:
    """
    Make one Gemini generate_content call and return the raw response text.

    Raises GeminiAPIError / GeminiConfigError on any SDK/network failure,
    or GeminiResponseError if the response body is empty. Never raises a
    raw SDK exception.
    """
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
    return text


def generate_json(system_instruction: str, prompt: str) -> dict:
    """
    Send `prompt` to Gemini (with `system_instruction`) requesting a JSON
    response, and return the parsed dict.

    Gemini is asked for `response_mime_type="application/json"`, but in
    practice sometimes still wraps output in markdown fences or adds
    explanatory text around the JSON. This is handled by a multi-step
    recovery parse (see _parse_gemini_json), and if that still fails, one
    automatic retry with a stronger formatting instruction — never more
    than one retry.

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

    text = _call_gemini(client, types, genai_errors, system_instruction, prompt)

    try:
        return _parse_gemini_json(text)
    except _JsonRecoveryFailed:
        logger.warning(
            "Gemini response could not be parsed as JSON after recovery attempts; "
            "retrying once with a stronger formatting instruction"
        )

    retry_text = _call_gemini(
        client, types, genai_errors, system_instruction, prompt + _RETRY_INSTRUCTION
    )
    try:
        result = _parse_gemini_json(retry_text)
        logger.info("Gemini JSON retry succeeded")
        return result
    except _JsonRecoveryFailed:
        logger.warning("Gemini JSON retry also failed to parse")
        raise GeminiResponseError(
            "Gemini's response could not be parsed. Please try regenerating."
        )

