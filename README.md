# HireLens — AI-assisted recruitment screening MVP

A runnable Flask + SQLite recruitment workflow with recruiter/client roles, requisition scorecards, bulk PDF/DOCX intake, duplicate detection, evidence-based scoring, client review, pipeline and synthetic demo data.

## Quick start
1. Python 3.10+ recommended.
2. `python -m venv .venv`
3. Activate it: Windows PowerShell `.venv\\Scripts\\Activate.ps1`; macOS/Linux `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and set strong random secret keys.
6. `python seed.py`
7. `python run.py`
8. Open http://127.0.0.1:5000

Demo logins (password for all: `HireLens@123`):
- recruiter@hirelens.demo
- client@hirelens.demo
- delivery@hirelens.demo

Sign in as recruiter and click **Load demo data** on the dashboard.

## AI scoring
Set `OPENAI_API_KEY` to enable OpenAI JSON-based evidence scoring. Without a key, the app uses a transparent keyword/regex fallback and labels the method. Both paths validate that quoted evidence exists in extracted CV text. Scores are advisory only; no automatic rejection is implemented.

## Important MVP limitations
- Scanned PDFs are detected when text extraction returns empty and are flagged for manual review. OCR is not implemented.
- Candidate name is initially derived from filename; recruiters must verify/edit it. CV parsing is intentionally conservative.
- Consent is stored as a boolean in the demo workflow; production requires a timestamp, purpose, notice version and source.
- SQLite is for local demo only. Use managed PostgreSQL and private object storage for production.
- This is a take-home MVP, not a DPDP compliance certification.
