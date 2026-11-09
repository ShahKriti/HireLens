# Deployment and local setup

## Local setup
1. Install Python 3.10 or newer.
2. Clone the public GitHub repository.
3. Create and activate a virtual environment.
4. Run `pip install -r requirements.txt`.
5. Copy `.env.example` to `.env`.
6. Set `FLASK_SECRET_KEY` and `JWT_SECRET_KEY` to unique random values. Optionally set `OPENAI_API_KEY` and `OPENAI_MODEL`.
7. Run `python seed.py`.
8. Run `python run.py` and visit `http://127.0.0.1:5000`.

## Demo credentials
Password for all accounts: `HireLens@123`
- Recruiter: `recruiter@hirelens.demo`
- Client hiring manager: `client@hirelens.demo`
- Delivery head: `delivery@hirelens.demo`

Use synthetic sample data only. The recruiter dashboard includes a **Load demo data** action.

## Environment variables (names only)
- `FLASK_SECRET_KEY`
- `JWT_SECRET_KEY`
- `DATABASE_PATH`
- `UPLOAD_FOLDER`
- `MAX_CONTENT_LENGTH_MB`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

## Deployment notes
The project is packaged as a single Flask service serving both API and static frontend. On a host such as Render:
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn run:app`
- Configure the environment variables above in the host dashboard.
- Attach persistent storage for SQLite and uploaded files for a demo deployment; for production, replace SQLite with managed PostgreSQL and uploads with private object storage.
- Set `FLASK_SECRET_KEY` and `JWT_SECRET_KEY` to strong generated secrets. Never commit `.env`.

## Production hardening still required
HTTPS, CSRF strategy for browser token storage, rate limiting, malware scanning, OCR pipeline, secure private file storage, database migrations, retention schedules, explicit consent receipts, client-to-requisition mapping, stronger tenant isolation, audit-log retention, monitoring and backups.
