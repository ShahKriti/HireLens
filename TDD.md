# HireLens — Technical Design Document

**GitHub URL:** [Add your public repository URL before submission]  
**Live application:** [Add deployment URL if deployed]  
**Version:** MVP / 9 November 2026

## 1. Executive summary
HireLens is a focused recruitment screening workflow for Company A. Recruiters create a role scorecard, upload PDF/DOCX CVs in batches, inspect ranked candidates with evidence, and submit candidates to a client portal. Client hiring managers can shortlist, reject with a reason, or propose an interview slot. A pipeline tracks candidate status.

## 2. Scope and assumptions
The Core Build is implemented as the primary scope. The following are explicit assumptions because the brief does not define them:
- **Assumption A1:** A single client account represents one client organisation; demo data uses Northstar Bank.
- **Assumption A2:** CV file size is bounded by the configured request limit (default 25 MB total request); batch count is capped at 500.
- **Assumption A3:** The demo uses a boolean consent flag; production must record timestamp, purpose, notice version and consent source.
- **Assumption A4:** Candidate profile fields are conservatively parsed. Recruiters must verify the original CV before submission.
- **Assumption A5:** CTC is stored on the scorecard but is not used for ranking unless a reliable candidate CTC field is added.
- **Assumption A6:** Scanned PDFs without extractable text are flagged for manual review; OCR is deferred.
- **Assumption A7:** Sample candidates and demo users are synthetic and use no real personal contact details.
- **Assumption A8:** SQLite is acceptable for a local take-home demo; production should use PostgreSQL.
- **Assumption A9:** The deterministic fallback is a transparent matching aid, not a substitute for the configured LLM scoring service.

## 3. Architecture
- **Frontend:** Responsive HTML/CSS/JavaScript served by Flask. This avoids a separate build chain for a time-boxed solo MVP.
- **Backend:** Flask REST API with JWT authentication and role decorators.
- **Database:** SQLite with relational tables for users, requisitions, candidates, applications and audit logs.
- **Parsing:** PyMuPDF extracts PDF text; python-docx extracts DOCX paragraphs.
- **Scoring:** OpenAI structured JSON response when configured; otherwise transparent keyword/regex fallback. The backend verifies every returned quote against extracted source text.
- **Deployment:** Single Flask web service. Static frontend and API share an origin.

## 4. Data model
- `users`: identity, password hash, role and optional client scope.
- `requisitions`: title, client, location, experience range, must-have skills, notice limit and optional CTC range.
- `candidates`: candidate code, parsed profile, extracted CV text, file metadata, consent flag and deletion marker.
- `applications`: requisition-candidate relationship, score, evidence JSON, status, submission flag, client decision and interview slot.
- `audit_logs`: user, candidate, action and timestamp for profile/CV access.

## 5. Main flows
1. Recruiter authenticates; JWT identifies the user and role.
2. Recruiter creates an editable scorecard.
3. Recruiter uploads PDF/DOCX files (up to 500). Files are parsed, empty/scanned documents are flagged, and duplicate text hashes are detected.
4. Profiles are associated with the requisition and scored. Ranking is advisory; no candidate is auto-rejected.
5. Recruiter opens the original CV (access is logged) and explicitly submits candidates to the client.
6. Client sees submitted candidates with contact fields masked and can shortlist, reject with a required reason, or propose an interview slot.
7. Recruiter/delivery users inspect the requisition pipeline.
8. Recruiter can record consent or request candidate deletion.

## 6. AI and automation design
The scoring prompt includes only extracted CV text and job criteria. It explicitly excludes name, gender, age, photo, marital status and other protected attributes. Output is structured JSON containing score, evidence criterion, match flag and verbatim quote. The service verifies each quote is a substring of source text; unverifiable quotes are marked unmatched. If the model is unavailable or returns invalid data, the transparent keyword fallback runs and labels itself. Missing evidence is not treated as proof that a candidate lacks a skill. Low scores remain searchable. Human review is required before client submission.

## 7. UI decisions
- Dark navy navigation creates a stable workspace frame; white panels and restrained teal accents keep the interface calm.
- Recruiter ranking emphasizes score, evidence and the next action.
- Client portal uses candidate codes and masks email/phone.
- Responsive navigation and horizontal scrolling support mobile use.
- Empty, loading, error and success feedback are provided through empty states, disabled upload action and toast messages.

## 8. Security and privacy
Passwords are hashed; API routes require JWT and role checks; input fields receive basic validation; secrets are environment variables; uploads accept only PDF/DOCX; client responses omit candidate name/contact details; profile access is logged; deletion removes CV text and application links from the active database. Use synthetic data only.
**Limit:** The demo tenant check is simplified and requires stronger client-to-requisition mapping before production. Deletion is not a certified backup purge. Production must implement retention controls, secure file storage, encryption, malware scanning and legal review under DPDP Act 2023.

## 9. Testing
Run `pytest`. Tests cover scoring evidence behavior and API health. Extend with authorization, duplicate upload, malformed file, cross-client isolation, consent and deletion tests before production.

## 10. What was cut / next steps
Cut: job-board integrations, scraping, video interviews, background verification, OCR for scanned CVs, external messaging, payment workflows, advanced analytics and production-grade tenant administration.
Next: OCR with confidence thresholds; PostgreSQL and object storage; consent receipts and retention workflows; strict client-requisition mapping; audit export; weekly AI-vs-recruiter rank sample; load testing for 500-file batches; stronger end-to-end tests.
