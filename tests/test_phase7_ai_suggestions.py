"""
tests/test_phase7_ai_suggestions.py
--------------------------------------
Unit tests for the Phase 7 Gemini AI suggestions pipeline.

The google.genai SDK is fully mocked via sys.modules injection — no real
network calls are ever made, and these tests pass whether or not the
real google-genai package happens to be installed in the environment.
"""

import sys
import types as pytypes
from types import SimpleNamespace

import pytest

from ai import gemini_service
from ai.gemini_service import GeminiAPIError, GeminiConfigError, GeminiResponseError
from ai.prompts import build_suggestions_prompt
from ai.recommendation import generate_resume_suggestions
from ai.schemas import AIResumeSuggestions
from ats.ats_score import generate_ats_report
from config import settings
from parser.entity_extractor import extract_contact_info
from parser.schemas import ParsedResume
from parser.section_parser import parse_sections
from parser.skill_extractor import extract_skills
from parser.text_cleaner import clean_text


SAMPLE_RESUME = """John Smith
john.smith@email.com | +1 555-123-4567

PROFESSIONAL SUMMARY
Aspiring software engineer.

WORK EXPERIENCE
Software Engineering Intern, Acme Corp
- Worked on Python automation.

PROJECTS
Resume Analyzer
- Built a Streamlit app.

TECHNICAL SKILLS
Python, Django, Git
"""

NO_EXPERIENCE_PROJECTS_RESUME = """Jane Doe
jane@example.com

PROFESSIONAL SUMMARY
Recent graduate looking for opportunities.

EDUCATION
B.Tech in Computer Science

TECHNICAL SKILLS
Python, SQL
"""


def _build_parsed_resume(text: str) -> ParsedResume:
    cleaned = clean_text(text)
    contact = extract_contact_info(cleaned)
    sections, order, _ = parse_sections(cleaned)
    return ParsedResume(
        source_filename="sample.pdf",
        file_type="pdf",
        raw_text=text,
        cleaned_text=cleaned,
        contact=contact,
        sections=sections,
        detected_section_order=order,
        parsing_warnings=[],
    )


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def reset_gemini_client():
    """Every test starts with a fresh (uninitialized) cached Gemini client."""
    gemini_service._client = None
    yield
    gemini_service._client = None


@pytest.fixture
def with_api_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "fake-test-key")


def _install_fake_genai(monkeypatch):
    """
    Install fake google.genai modules into sys.modules for the duration of
    a test. Returns (FakeAPIError, set_response) where set_response(fn)
    controls what client.models.generate_content(...) returns/raises.
    """
    fake_google = pytypes.ModuleType("google")
    fake_genai = pytypes.ModuleType("google.genai")
    fake_genai_types = pytypes.ModuleType("google.genai.types")
    fake_genai_errors = pytypes.ModuleType("google.genai.errors")

    class FakeAPIError(Exception):
        def __init__(self, message, code=None):
            super().__init__(message)
            self.message = message
            self.code = code

    fake_genai_errors.APIError = FakeAPIError

    class FakeGenerateContentConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_genai_types.GenerateContentConfig = FakeGenerateContentConfig

    box = {"fn": lambda model, contents, config: SimpleNamespace(text="{}")}

    def set_response(fn):
        box["fn"] = fn

    class FakeModels:
        def generate_content(self, model, contents, config):
            return box["fn"](model, contents, config)

    class FakeClient:
        def __init__(self, api_key=None):
            self.models = FakeModels()

    fake_genai.Client = FakeClient
    fake_google.genai = fake_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_genai_types)
    monkeypatch.setitem(sys.modules, "google.genai.errors", fake_genai_errors)

    return FakeAPIError, set_response


VALID_RESPONSE_JSON = """
{
  "summary": {"original": "Aspiring software engineer.", "improved": "Improved summary.", "concise": "Concise.", "target_role_focused": null},
  "experience": [
    {"original": "Worked on Python automation.", "improved": "Developed Python automation scripts.", "reason": "Stronger verb, more specific."}
  ],
  "projects": [
    {"project_name": "Resume Analyzer", "original": "Built a Streamlit app.", "improved_bullets": ["Built a Streamlit-based resume analyzer."], "technologies": ["Python"], "action_verbs": ["Developed"], "suggestions": ["Add a metric for usage."]}
  ],
  "weaknesses": [
    {"priority": "High Priority", "issue": "No metrics", "recommendation": "Add measurable outcomes."}
  ],
  "job_specific_suggestions": []
}
"""


# --------------------------------------------------------------------------- #
# Gemini service — config / key handling
# --------------------------------------------------------------------------- #

def test_is_configured_false_without_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    assert gemini_service.is_configured() is False


def test_is_configured_true_with_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "some-key")
    assert gemini_service.is_configured() is True


def test_missing_api_key_raises_config_error(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    with pytest.raises(GeminiConfigError):
        gemini_service.generate_json("system", "prompt")


def test_missing_api_key_message_does_not_leak_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    with pytest.raises(GeminiConfigError) as exc_info:
        gemini_service.generate_json("system", "prompt")
    assert "GEMINI_API_KEY" in str(exc_info.value)
    assert "None" not in str(exc_info.value)


# --------------------------------------------------------------------------- #
# Gemini service — successful and error responses (mocked SDK)
# --------------------------------------------------------------------------- #

def test_generate_json_success(monkeypatch, with_api_key):
    _install_fake_genai(monkeypatch)
    result = gemini_service.generate_json("system", "prompt")
    assert result == {}


def test_generate_json_parses_real_payload(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text=VALID_RESPONSE_JSON))
    result = gemini_service.generate_json("system", "prompt")
    assert result["summary"]["improved"] == "Improved summary."


def test_generate_json_empty_response_raises(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text=""))
    with pytest.raises(GeminiResponseError):
        gemini_service.generate_json("system", "prompt")


def test_generate_json_invalid_json_raises(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text="not valid json{"))
    with pytest.raises(GeminiResponseError):
        gemini_service.generate_json("system", "prompt")


def test_generate_json_rate_limit_raises_api_error(monkeypatch, with_api_key):
    FakeAPIError, set_response = _install_fake_genai(monkeypatch)

    def raise_rate_limit(model, contents, config):
        raise FakeAPIError("rate limited", code=429)

    set_response(raise_rate_limit)
    with pytest.raises(GeminiAPIError):
        gemini_service.generate_json("system", "prompt")


def test_generate_json_auth_error_raises_config_error(monkeypatch, with_api_key):
    FakeAPIError, set_response = _install_fake_genai(monkeypatch)

    def raise_auth_error(model, contents, config):
        raise FakeAPIError("invalid key", code=401)

    set_response(raise_auth_error)
    with pytest.raises(GeminiConfigError):
        gemini_service.generate_json("system", "prompt")


def test_generate_json_server_error_raises_api_error(monkeypatch, with_api_key):
    FakeAPIError, set_response = _install_fake_genai(monkeypatch)

    def raise_server_error(model, contents, config):
        raise FakeAPIError("server error", code=503)

    set_response(raise_server_error)
    with pytest.raises(GeminiAPIError):
        gemini_service.generate_json("system", "prompt")


def test_generate_json_network_error_raises_api_error(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)

    def raise_network_error(model, contents, config):
        raise ConnectionError("network unreachable")

    set_response(raise_network_error)
    with pytest.raises(GeminiAPIError):
        gemini_service.generate_json("system", "prompt")


# --------------------------------------------------------------------------- #
# Prompt generation
# --------------------------------------------------------------------------- #

def test_build_suggestions_prompt_excludes_contact_info():
    parsed = _build_parsed_resume(SAMPLE_RESUME)
    cleaned = clean_text(SAMPLE_RESUME)
    skill_result = extract_skills(cleaned)
    ats_report = generate_ats_report(parsed, skill_result)

    prompt = build_suggestions_prompt(parsed, skill_result, ats_report, target_role="Backend Engineer")

    assert "john.smith@email.com" not in prompt
    assert "555-123-4567" not in prompt
    assert "Backend Engineer" in prompt
    assert "Python" in prompt  # detected skill should be present


def test_build_suggestions_prompt_no_job_description_excludes_match_section():
    parsed = _build_parsed_resume(SAMPLE_RESUME)
    cleaned = clean_text(SAMPLE_RESUME)
    skill_result = extract_skills(cleaned)
    ats_report = generate_ats_report(parsed, skill_result)

    prompt = build_suggestions_prompt(parsed, skill_result, ats_report, match_report=None)
    assert "JOB DESCRIPTION MATCH" not in prompt


def test_build_suggestions_prompt_no_experience_or_projects_shows_placeholder():
    parsed = _build_parsed_resume(NO_EXPERIENCE_PROJECTS_RESUME)
    cleaned = clean_text(NO_EXPERIENCE_PROJECTS_RESUME)
    skill_result = extract_skills(cleaned)
    ats_report = generate_ats_report(parsed, skill_result)

    prompt = build_suggestions_prompt(parsed, skill_result, ats_report)
    assert "=== EXPERIENCE ===\n(none detected)" in prompt
    assert "=== PROJECTS ===\n(none detected)" in prompt


# --------------------------------------------------------------------------- #
# End-to-end recommendation generation (mocked SDK)
# --------------------------------------------------------------------------- #

def test_generate_resume_suggestions_empty_resume_raises_without_api_call():
    empty_parsed = _build_parsed_resume("")
    skill_result = extract_skills("")
    ats_report = generate_ats_report(empty_parsed, skill_result)

    with pytest.raises(GeminiResponseError):
        generate_resume_suggestions(empty_parsed, skill_result, ats_report)


def test_generate_resume_suggestions_success(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text=VALID_RESPONSE_JSON))

    parsed = _build_parsed_resume(SAMPLE_RESUME)
    cleaned = clean_text(SAMPLE_RESUME)
    skill_result = extract_skills(cleaned)
    ats_report = generate_ats_report(parsed, skill_result)

    result = generate_resume_suggestions(parsed, skill_result, ats_report)

    assert isinstance(result, AIResumeSuggestions)
    assert result.summary.improved == "Improved summary."
    assert len(result.experience) == 1
    assert result.experience[0].improved == "Developed Python automation scripts."
    assert len(result.projects) == 1
    assert result.weaknesses[0].priority == "High Priority"
    assert result.job_specific_suggestions == []


def test_generate_resume_suggestions_no_experience_no_projects(monkeypatch, with_api_key):
    response_json = """
    {"summary": {"original": null, "improved": "x", "concise": "x", "target_role_focused": null},
     "experience": [], "projects": [], "weaknesses": [], "job_specific_suggestions": []}
    """
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text=response_json))

    parsed = _build_parsed_resume(NO_EXPERIENCE_PROJECTS_RESUME)
    cleaned = clean_text(NO_EXPERIENCE_PROJECTS_RESUME)
    skill_result = extract_skills(cleaned)
    ats_report = generate_ats_report(parsed, skill_result)

    result = generate_resume_suggestions(parsed, skill_result, ats_report)
    assert result.experience == []
    assert result.projects == []


def test_generate_resume_suggestions_job_specific_normalizes_category(monkeypatch, with_api_key):
    response_json = """
    {"summary": null, "experience": [], "projects": [], "weaknesses": [],
     "job_specific_suggestions": [
        {"category": "already strong", "detail": "Python matches the JD requirement."},
        {"category": "missing skill area", "detail": "Consider learning Kubernetes if relevant to your target role."}
     ]}
    """
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text=response_json))

    parsed = _build_parsed_resume(SAMPLE_RESUME)
    cleaned = clean_text(SAMPLE_RESUME)
    skill_result = extract_skills(cleaned)
    ats_report = generate_ats_report(parsed, skill_result)

    result = generate_resume_suggestions(parsed, skill_result, ats_report)
    categories = [s.category for s in result.job_specific_suggestions]
    assert "Already Strong" in categories
    assert "Missing" in categories


def test_generate_resume_suggestions_invalid_response_raises_response_error(monkeypatch, with_api_key):
    # Missing required "improved" field on an experience item -> schema validation should fail
    malformed_json = """
    {"summary": null, "experience": [{"original": "did stuff"}], "projects": [], "weaknesses": [], "job_specific_suggestions": []}
    """
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text=malformed_json))

    parsed = _build_parsed_resume(SAMPLE_RESUME)
    cleaned = clean_text(SAMPLE_RESUME)
    skill_result = extract_skills(cleaned)
    ats_report = generate_ats_report(parsed, skill_result)

    with pytest.raises(GeminiResponseError):
        generate_resume_suggestions(parsed, skill_result, ats_report)


def test_generate_resume_suggestions_api_error_propagates(monkeypatch, with_api_key):
    FakeAPIError, set_response = _install_fake_genai(monkeypatch)

    def raise_rate_limit(model, contents, config):
        raise FakeAPIError("rate limited", code=429)

    set_response(raise_rate_limit)

    parsed = _build_parsed_resume(SAMPLE_RESUME)
    cleaned = clean_text(SAMPLE_RESUME)
    skill_result = extract_skills(cleaned)
    ats_report = generate_ats_report(parsed, skill_result)

    with pytest.raises(GeminiAPIError):
        generate_resume_suggestions(parsed, skill_result, ats_report)


# --------------------------------------------------------------------------- #
# JSON recovery / single-retry pipeline (production bug fix — Gemini
# sometimes ignores response_mime_type="application/json" and wraps the
# JSON in markdown fences or explanatory prose)
# --------------------------------------------------------------------------- #

def test_generate_json_plain_json_parses_immediately(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text='{"a": 1}'))
    result = gemini_service.generate_json("system", "prompt")
    assert result == {"a": 1}


def test_generate_json_recovers_markdown_fenced_json(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text='```json\n{"a": 2}\n```'))
    result = gemini_service.generate_json("system", "prompt")
    assert result == {"a": 2}


def test_generate_json_recovers_bare_fenced_json_without_language_tag(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text='```\n{"a": 3}\n```'))
    result = gemini_service.generate_json("system", "prompt")
    assert result == {"a": 3}


def test_generate_json_recovers_json_surrounded_by_explanatory_text(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    surrounded = 'Sure, here is the analysis:\n\n{"a": 4}\n\nLet me know if you need anything else!'
    set_response(lambda model, contents, config: SimpleNamespace(text=surrounded))
    result = gemini_service.generate_json("system", "prompt")
    assert result == {"a": 4}


def test_generate_json_retry_succeeds_after_first_response_unparseable(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    call_count = {"n": 0}

    def responder(model, contents, config):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return SimpleNamespace(text="Sorry, I can't help with that right now.")
        # Second call (the retry) includes the stronger instruction in the prompt
        assert "Return ONLY valid JSON" in contents
        return SimpleNamespace(text='{"a": 5}')

    set_response(responder)
    result = gemini_service.generate_json("system", "prompt")
    assert result == {"a": 5}
    assert call_count["n"] == 2  # exactly one retry, not more


def test_generate_json_retry_also_fails_raises_response_error(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    call_count = {"n": 0}

    def responder(model, contents, config):
        call_count["n"] += 1
        return SimpleNamespace(text="still not JSON, sorry")

    set_response(responder)
    with pytest.raises(GeminiResponseError):
        gemini_service.generate_json("system", "prompt")
    assert call_count["n"] == 2  # original attempt + exactly one retry, never more


def test_generate_json_malformed_json_raises_response_error(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text="{unterminated: true"))
    with pytest.raises(GeminiResponseError):
        gemini_service.generate_json("system", "prompt")


def test_extract_largest_json_object_picks_largest_candidate():
    text = 'small: {"x": 1} but the real one is {"a": {"nested": true}, "b": [1, 2, 3]}'
    extracted = gemini_service._extract_largest_json_object(text)
    assert extracted == '{"a": {"nested": true}, "b": [1, 2, 3]}'


def test_strip_markdown_fences_removes_language_tag_and_fences():
    text = '```json\n{"a": 1}\n```'
    assert gemini_service._strip_markdown_fences(text) == '{"a": 1}'


def test_strip_markdown_fences_noop_on_plain_json():
    text = '{"a": 1}'
    assert gemini_service._strip_markdown_fences(text) == '{"a": 1}'

