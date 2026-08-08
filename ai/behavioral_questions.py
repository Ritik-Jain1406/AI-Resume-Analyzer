"""
ai/behavioral_questions.py
------------------------------
Phase 10 extra feature: static HR/Behavioral interview questions.

Deliberately static and deterministic — these are generic, universally
applicable questions that don't depend on resume content, so there's no
reason to involve Gemini (and no hallucination risk either). Always
available, with or without a configured Gemini API key.
"""

from __future__ import annotations

from ai.schemas import InterviewQuestion

BEHAVIORAL_QUESTIONS: list[InterviewQuestion] = [
    InterviewQuestion(question="Tell me about yourself.", difficulty="Easy", category="Behavioral", source="static"),
    InterviewQuestion(question="Walk me through your resume.", difficulty="Easy", category="Behavioral", source="static"),
    InterviewQuestion(question="Why should we hire you?", difficulty="Medium", category="Behavioral", source="static"),
    InterviewQuestion(question="Describe a difficult bug you solved.", difficulty="Medium", category="Behavioral", source="static"),
    InterviewQuestion(question="Explain your resume analyzer (or a similar project) as if I've never seen it.", difficulty="Medium", category="Behavioral", source="static"),
    InterviewQuestion(question="What challenges did you face on a recent project, and how did you handle them?", difficulty="Medium", category="Behavioral", source="static"),
    InterviewQuestion(question="Tell me about a time you worked closely with a team to get something done.", difficulty="Medium", category="Behavioral", source="static"),
    InterviewQuestion(question="What's your biggest strength?", difficulty="Easy", category="Behavioral", source="static"),
    InterviewQuestion(question="What's your biggest weakness?", difficulty="Hard", category="Behavioral", source="static"),
    InterviewQuestion(question="Where do you see yourself in five years?", difficulty="Medium", category="Behavioral", source="static"),
]


def get_behavioral_questions() -> list[InterviewQuestion]:
    """Return the full static HR/behavioral question set."""
    return list(BEHAVIORAL_QUESTIONS)
