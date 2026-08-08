"""
tests/test_phase10_interview_prep.py
----------------------------------------
Unit tests for the Phase 10 interview preparation pipeline.

Skill-based and behavioral questions are pure/static and tested directly.
Project-based questions go through the exact same mocked-SDK technique as
Phase 7's tests (sys.modules injection, no real Gemini calls) since
ai/interview_preparation.py reuses ai/gemini_service.generate_json()
rather than duplicating any API logic.
"""

import sys
import types as pytypes
from types import SimpleNamespace

import pytest

from ai import gemini_service
from ai.behavioral_questions import BEHAVIORAL_QUESTIONS, get_behavioral_questions
from ai.interview_preparation import (
    build_interview_prep,
    get_project_questions,
    get_skill_questions,
    load_interview_question_bank,
)
from ai.schemas import InterviewPrepResult, InterviewQuestion
from config import settings
from parser.schemas import SkillExtractionResult


def _make_skill_result(detected: list[str]) -> SkillExtractionResult:
    return SkillExtractionResult(
        detected_by_category={"Programming": detected},
        missing_by_category={"Programming": []},
        all_detected=detected,
        all_known_categories=["Programming"],
    )


# --------------------------------------------------------------------------- #
# Static skill-based question bank
# --------------------------------------------------------------------------- #

def test_interview_question_bank_loads():
    bank = load_interview_question_bank()
    assert not bank.empty
    assert set(bank.columns) >= {"skill", "difficulty", "question"}


def test_interview_question_bank_covers_common_skills():
    bank = load_interview_question_bank()
    skills_present = set(bank["skill"])
    assert {"Python", "Git", "Docker", "SQL", "React"}.issubset(skills_present)


def test_get_skill_questions_returns_curated_questions_for_known_skill():
    skill_result = _make_skill_result(["Python"])
    questions = get_skill_questions(skill_result)
    assert len(questions) >= 1
    assert all(q.category == "Skill" for q in questions)
    assert all(q.source == "static" for q in questions)
    assert all(q.related_to == "Python" for q in questions)


def test_get_skill_questions_covers_all_three_difficulties_for_curated_skill():
    skill_result = _make_skill_result(["Python"])
    questions = get_skill_questions(skill_result)
    difficulties = {q.difficulty for q in questions}
    assert difficulties == {"Easy", "Medium", "Hard"}


def test_get_skill_questions_fallback_for_unknown_skill():
    skill_result = _make_skill_result(["SomeCompletelyMadeUpSkillXYZ"])
    questions = get_skill_questions(skill_result)
    assert len(questions) == 1
    assert "SomeCompletelyMadeUpSkillXYZ" in questions[0].question
    assert questions[0].source == "static"


def test_get_skill_questions_empty_when_no_skills_detected():
    skill_result = _make_skill_result([])
    questions = get_skill_questions(skill_result)
    assert questions == []


def test_get_skill_questions_no_skill_silently_dropped():
    skill_result = _make_skill_result(["Python", "SomeMadeUpSkill123"])
    questions = get_skill_questions(skill_result)
    related = {q.related_to for q in questions}
    assert "Python" in related
    assert "SomeMadeUpSkill123" in related  # fallback question, not dropped


# --------------------------------------------------------------------------- #
# Static HR/Behavioral question bank
# --------------------------------------------------------------------------- #

def test_behavioral_questions_always_available():
    questions = get_behavioral_questions()
    assert len(questions) == len(BEHAVIORAL_QUESTIONS)
    assert all(q.category == "Behavioral" for q in questions)
    assert all(q.source == "static" for q in questions)


def test_behavioral_questions_include_required_examples():
    questions = {q.question for q in get_behavioral_questions()}
    assert "Tell me about yourself." in questions
    assert "Why should we hire you?" in questions
    assert "What's your biggest weakness?" in questions


def test_behavioral_questions_returns_a_copy_not_the_shared_list():
    q1 = get_behavioral_questions()
    q1.append(InterviewQuestion(question="test", difficulty="Easy", category="Behavioral", source="static"))
    q2 = get_behavioral_questions()
    assert len(q2) == len(BEHAVIORAL_QUESTIONS)  # mutation of q1 must not leak


# --------------------------------------------------------------------------- #
# Gemini project questions — fully mocked SDK (same technique as Phase 7)
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def reset_gemini_client():
    gemini_service._client = None
    yield
    gemini_service._client = None


@pytest.fixture
def with_api_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "fake-test-key")


def _install_fake_genai(monkeypatch):
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


def test_get_project_questions_no_content_returns_empty_no_warning():
    questions, warnings = get_project_questions(None, None)
    assert questions == []
    assert warnings == []


def test_get_project_questions_missing_api_key_returns_warning(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    questions, warnings = get_project_questions("Some experience text.", None)
    assert questions == []
    assert len(warnings) == 1
    assert "Gemini API key is not configured" in warnings[0]


def test_get_project_questions_success(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    response_json = (
        '{"questions": ['
        '{"question": "Why did you choose Django for this project?", "difficulty": "Medium", "related_to": "Resume Analyzer"}'
        "]}"
    )
    set_response(lambda model, contents, config: SimpleNamespace(text=response_json))

    questions, warnings = get_project_questions("Built things.", "Resume Analyzer project.")
    assert warnings == []
    assert len(questions) == 1
    assert questions[0].category == "Project"
    assert questions[0].source == "gemini"  # set by our code, not trusted from the model
    assert questions[0].difficulty == "Medium"
    assert questions[0].related_to == "Resume Analyzer"


def test_get_project_questions_malformed_response_returns_warning_not_crash(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    set_response(lambda model, contents, config: SimpleNamespace(text="not json at all"))

    questions, warnings = get_project_questions("Built things.", None)
    assert questions == []
    assert len(warnings) == 1


def test_get_project_questions_api_error_returns_warning_not_raise(monkeypatch, with_api_key):
    FakeAPIError, set_response = _install_fake_genai(monkeypatch)

    def raise_rate_limit(model, contents, config):
        raise FakeAPIError("rate limited", code=429)

    set_response(raise_rate_limit)
    questions, warnings = get_project_questions("Built things.", None)
    assert questions == []
    assert len(warnings) == 1
    assert "rate limit" in warnings[0].lower()


# --------------------------------------------------------------------------- #
# build_interview_prep — full orchestration
# --------------------------------------------------------------------------- #

def test_build_interview_prep_without_project_questions():
    skill_result = _make_skill_result(["Python", "Git"])
    result = build_interview_prep(
        skill_result=skill_result,
        experience_text="Some experience.",
        projects_text=None,
        include_project_questions=False,
    )
    assert isinstance(result, InterviewPrepResult)
    assert result.skill_questions
    assert result.project_questions == []
    assert result.behavioral_questions
    assert result.warnings == []


def test_build_interview_prep_with_project_questions_no_key_configured(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    skill_result = _make_skill_result(["Python"])
    result = build_interview_prep(
        skill_result=skill_result,
        experience_text="Built REST APIs.",
        projects_text=None,
        include_project_questions=True,
    )
    assert result.project_questions == []
    assert result.gemini_available is False
    assert len(result.warnings) == 1
    assert result.skill_questions
    assert result.behavioral_questions


def test_build_interview_prep_with_project_questions_success(monkeypatch, with_api_key):
    _, set_response = _install_fake_genai(monkeypatch)
    response_json = '{"questions": [{"question": "Tell me more.", "difficulty": "Hard", "related_to": "Backend"}]}'
    set_response(lambda model, contents, config: SimpleNamespace(text=response_json))

    skill_result = _make_skill_result(["Python"])
    result = build_interview_prep(
        skill_result=skill_result,
        experience_text="Built backend systems.",
        projects_text=None,
        include_project_questions=True,
    )
    assert len(result.project_questions) == 1
    assert result.project_questions[0].source == "gemini"
    assert result.gemini_available is True
    assert result.skill_questions
    assert result.behavioral_questions


def test_build_interview_prep_no_resume_content_at_all():
    skill_result = _make_skill_result([])
    result = build_interview_prep(
        skill_result=skill_result,
        experience_text=None,
        projects_text=None,
        include_project_questions=True,
    )
    assert result.skill_questions == []
    assert result.project_questions == []
    assert result.behavioral_questions  # always present regardless of resume content
