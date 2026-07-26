# AI Resume Analyzer

An AI-powered resume analysis tool built with Python and Streamlit. It checks
ATS (Applicant Tracking System) compatibility, matches resumes against job
descriptions, identifies skill gaps, and generates AI-powered improvement
suggestions — all through an interactive dashboard.

> **Status:** 🚧 Phase 1 — project scaffold complete. Parsing, scoring, and
> matching features are being built out phase by phase.

## Features (planned)

- 📄 Resume parsing (PDF & DOCX) into structured data
- ✅ ATS compatibility scoring with section-wise breakdown
- 🎯 Job description matching (semantic + keyword + skill-based)
- 📊 Skill gap analysis with a prioritized learning roadmap
- ✍️ AI-generated suggestions for summary, experience, and project bullets
- 📈 Interactive dashboard (ATS score, skill distribution, match %)
- 🔁 Resume version comparison
- 🎤 Interview question generation based on the resume's content
- 🗂️ Resume history with search/filter

## Tech Stack

| Layer          | Tools |
|----------------|-------|
| Frontend       | Streamlit |
| Backend        | Python 3.12+ |
| NLP / ML       | spaCy, NLTK, scikit-learn, sentence-transformers |
| Parsing        | PyMuPDF, pdfplumber, python-docx |
| Visualization  | Plotly, Matplotlib |
| Database       | SQLite |
| Logging        | Loguru |

## Project Structure

```
AI-Resume-Analyzer/
├── app.py                # Streamlit entry point
├── config.py             # Centralized settings (pydantic)
├── requirements.txt
├── parser/               # Resume text/section/entity extraction
├── ats/                  # ATS scoring logic
├── matching/             # Resume ↔ job description matching
├── ai/                   # Recommendation & suggestion generation
├── visualization/        # Charts & dashboard components
├── database/             # SQLite models & data access
├── utils/                # Shared helpers, constants, logger, validators
├── data/                 # Skills DB, sample resumes & job descriptions
├── tests/                # Unit tests
└── docs/                 # Documentation
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

### 3. (Optional) Configure environment variables

Copy `.env.example` to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

### 4. Run the app

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

## Development

- Config lives in `config.py` — don't hard-code paths or thresholds elsewhere.
- Logging goes through `utils/logger.py` (`get_logger(__name__)`), writing to
  both the console and `logs/app.log`.
- Run tests with:

  ```bash
  pytest --cov=. tests/
  ```

## Roadmap

See `docs/roadmap.md` for the full phase-by-phase build plan (parsing → ATS
scoring → job matching → skill gap analysis → AI suggestions → dashboard →
comparison → interview prep → admin/history → deployment).

## License

MIT — see `LICENSE`.
