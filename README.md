# AI Resume Analyzer

An AI-powered resume analysis tool built with Python and Streamlit. It parses
resumes, checks ATS (Applicant Tracking System) compatibility, matches
resumes against job descriptions, identifies skill gaps, and generates
AI-powered improvement suggestions — all through an interactive dashboard.

> **Status:** Phases 1–10 implemented and tested. Phases 11–12
> (admin/history, deployment) are not yet built.

## Features

- 📄 **Resume parsing** (PDF & DOCX) into structured contact info + sections
- 🧠 **Skill extraction** against an 80+ skill categorized database (with
  alias resolution and fuzzy matching)
- ✅ **ATS compatibility scoring** — weighted, section-wise breakdown with
  ranked suggestions
- 🎯 **Job description matching** — semantic similarity (sentence
  embeddings) + TF-IDF cosine similarity + keyword coverage + skill match
- 📈 **Skill gap analysis** — missing skills prioritized High/Medium/Low,
  with learning resources and a phased roadmap
- 🤖 **AI Resume Suggestions** (Phase 7, Google Gemini) — improved summary
  versions, bullet-by-bullet rewrites with explanations, project
  improvements, prioritized weaknesses, and job-specific recommendations
- 📊 **Interactive Dashboard** (Phase 8) — ATS score gauge, skill
  distribution, resume-strength radar, weak-sections bar, job match
  visualizations, and a pipeline overview — strictly presentation-only,
  reads existing results rather than recomputing anything
- 🔀 **Resume Comparison** (Phase 9) — compare two resume versions side
  by side: ATS score delta (points + %), skills/keywords added or
  removed, and a deterministic (non-LLM) verdict on which is stronger.
  Fully independent of the single-resume session state used elsewhere.
- 🎤 **Interview Preparation** (Phase 10) — hybrid question generator:
  a static, curated skill-based question bank (Easy/Medium/Hard, no API
  call), Gemini-generated project/experience-specific questions (only on
  explicit request, reusing Phase 7's service), and a static HR/Behavioral
  question set. Skill and behavioral questions work fully even without a
  Gemini key.

## Tech Stack

| Layer          | Tools |
|----------------|-------|
| Frontend       | Streamlit |
| Backend        | Python 3.12+ |
| NLP / ML       | spaCy, scikit-learn, sentence-transformers, rapidfuzz |
| AI suggestions | Google Gemini (`google-genai` SDK) |
| Parsing        | PyMuPDF, pdfplumber, python-docx |
| Database       | SQLite (planned, not yet wired up) |
| Logging        | Loguru |

## Project Structure

```
AI-Resume-Analyzer/
├── app.py                     # Streamlit entry point (page routing)
├── config.py                  # Centralized settings (pydantic-settings, reads .env)
├── requirements.txt
├── parser/                    # Phase 2-3: text extraction, sections, entities, skills
├── ats/                       # Phase 4: ATS scoring checks + orchestrator
├── matching/                  # Phase 5-6: job matching + skill gap analysis
├── ai/                        # Phase 7: Gemini service, prompts, schemas, orchestrator
│   ├── gemini_service.py      #   - only module that touches the google-genai SDK
│   ├── prompts.py             #   - system instruction + prompt building (no API calls)
│   ├── schemas.py             #   - pydantic validation for Gemini's JSON output
│   ├── recommendation.py      #   - orchestrator: Phase 1-6 data -> prompt -> validated result
│   └── action_verb_reference.py  # static categorized verb list (no API call)
├── visualization/              # Phase 8: dashboard charts + layout (read-only, no new analysis)
│   ├── charts.py               #   - pure functions: existing model -> plotly Figure
│   └── dashboard.py            #   - layout/composition + session-state gating
├── comparison/                 # Phase 9: resume comparison (independent of Phase 1-8 session state)
│   ├── diff_engine.py          #   - pure functions: two already-computed results -> deltas
│   └── comparison_service.py   #   - orchestrator: calls parse_resume/extract_skills/generate_ats_report twice
├── utils/                     # Shared helpers, constants, logger, validators
├── data/                      # Skills DB, sample resumes & job descriptions
├── tests/                     # Unit tests (one file per phase)
└── docs/                      # Documentation
```

## Getting Started

### 1. Clone and set up a virtual environment

```bash
git clone <your-repo-url>
cd AI-Resume-Analyzer
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Configure environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Then edit `.env` and fill in your Gemini API key (see below). Every other
value in `.env.example` has a working default — you only need to touch
`GEMINI_API_KEY` to enable AI Resume Suggestions.

### 4. Run the app

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`. The first time you
use **Job Matching**, expect a pause while the semantic similarity model
downloads (~80MB, one-time, cached after that).

## Setting up the Gemini API key (Phase 7)

AI Resume Suggestions uses [Google Gemini](https://ai.google.dev/) via the
official `google-genai` Python SDK. Without a key, every other page (Resume
Upload, ATS Analysis, Job Matching, Skill Gap) still works fully — only the
AI Suggestions page is disabled, with a clear message telling you what to do.

1. Create a free API key at <https://aistudio.google.com/apikey>.
2. Copy `.env.example` to `.env` if you haven't already.
3. Add your key:

   ```
   GEMINI_API_KEY=your_key_here
   ```

4. (Optional) Override the model via `GEMINI_MODEL` in `.env` — defaults to
   `gemini-2.5-flash`. Gemini model names change fairly often; check
   <https://ai.google.dev/gemini-api/docs/models> for current options if the
   default ever stops working.
5. Run the app normally — the AI Suggestions page will detect the key
   automatically.

**The key is never hardcoded, never logged, and never shown in the UI or in
error messages.** It's read once from the `GEMINI_API_KEY` environment
variable via `config.py`, and `.env` is already listed in `.gitignore` so it
can't be committed by accident.

## How AI Suggestions work

The AI Suggestions page (`ai/` package) does **not** replace any of the
deterministic Phases 1–6 — it consumes their output:

```
Resume → Parser (Phase 2) → Skill Extraction (Phase 3) → ATS Analysis (Phase 4)
       → [optional] Job Matching (Phase 5) → [optional] Skill Gap (Phase 6)
       → ai/prompts.py builds a structured prompt from all of the above
       → ai/gemini_service.py calls Gemini, requesting JSON output
       → ai/schemas.py validates the response (malformed output is caught,
         never shown raw, and never crashes the app)
       → app.py renders it
```

Gemini is called **only** when you click "Generate Suggestions" /
"Regenerate Suggestions" — never automatically on page load or rerun.

The system prompt instructs Gemini (acting as "an experienced technical
recruiter and professional resume editor") to never fabricate experience,
metrics, skills, or certifications, and to point out *where* a real metric
could be added rather than inventing one. "Better Action Verbs" is a static
curated list (no API call — zero hallucination risk for that piece).

## Privacy considerations

- **Contact info is never sent to Gemini.** `ai/prompts.py` deliberately
  excludes name, email, phone, and social links from the prompt — only
  resume section text, detected skills, and (if present) job description /
  ATS findings are included, since none of the excluded fields are needed
  to improve wording.
- **Logs contain no resume content and no API key** — only technical
  metadata (e.g. prompt character count, HTTP error codes).
- Nothing from Phase 7 is persisted to disk; suggestions live only in the
  Streamlit session and are gone when the session ends (unless you use the
  download button).

## Testing

```bash
pytest tests/
```

Phase 7 tests (`tests/test_phase7_ai_suggestions.py`) fully mock the
`google-genai` SDK via `sys.modules` injection — **no real API calls are
made during automated tests**, and they pass with or without a configured
API key. Coverage includes: missing API key, successful generation,
empty/malformed/invalid-JSON responses, rate limiting (429), auth errors
(401/403), model-not-found (404), server errors (5xx), network failures,
prompt content (contact-info exclusion, no-JD / no-experience / no-projects
placeholders), and job-specific suggestion category normalization.

## Known limitations

- **Semantic matching (Phase 5)** needs internet on its *first* use to
  download the sentence-transformers model; after that it's cached and
  works offline. If it can't load, matching automatically falls back to
  TF-IDF/keyword-only scoring with a visible warning.
- **AI Suggestions (Phase 7)** requires internet and a valid Gemini API key
  for every generation — there's no offline fallback for this page, by
  design (there's no deterministic substitute for LLM-quality rewriting).
- Gemini's output is validated against a strict schema but is still
  probabilistic — occasional regeneration may be needed for the best
  phrasing, even though fabrication is explicitly disallowed in the prompt.
- Section/entity parsing (Phase 2) is heuristic, not ML-based — resumes with
  very unconventional formatting may need manual review of what was
  detected.
- No persistence/database layer yet (Phase 11); nothing survives a page
  refresh except what's cached in the current Streamlit session.

## Development

- Config lives in `config.py` — don't hard-code paths, thresholds, or the
  Gemini API key elsewhere.
- Logging goes through `utils/logger.py` (`get_logger(__name__)`), writing
  to both the console and `logs/app.log`.
- Run tests with `pytest tests/` (or `pytest --cov=. tests/` for coverage).

## Roadmap

See `docs/roadmap.md` for the full phase-by-phase build plan. Phases 1–7 are
complete; Phase 8 (dashboard visualizations) is next.

## License

MIT — see `LICENSE`.
