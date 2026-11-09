import json
import os
import re
import urllib.request
import urllib.error


def keyword_score(cv_text, scorecard):
    """Transparent fallback when the local AI model is unavailable."""
    cv_text = cv_text or ""
    text = cv_text.lower()
    scorecard = scorecard or {}

    must = [
        str(x).strip()
        for x in scorecard.get("must_have", [])
        if str(x).strip()
    ]

    evidence = []
    matched = 0

    for skill in must:
        found = re.search(re.escape(skill.lower()), text)

        if found:
            start = max(0, found.start() - 90)
            end = min(len(cv_text), found.end() + 120)
            quote = " ".join(cv_text[start:end].split())

            evidence.append({
                "criterion": skill,
                "matched": True,
                "quote": quote[:260]
            })
            matched += 1
        else:
            evidence.append({
                "criterion": skill,
                "matched": False,
                "quote": "No supporting phrase found in extracted CV text."
            })

    try:
        min_exp = float(scorecard.get("min_experience", 0) or 0)
    except (TypeError, ValueError):
        min_exp = 0

    exp_match = re.search(
        r'(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)',
        text
    )

    exp_val = float(exp_match.group(1)) if exp_match else None
    exp_ok = exp_val is not None and exp_val >= min_exp

    evidence.append({
        "criterion": "Experience",
        "matched": exp_ok,
        "quote": (
            f"CV mentions {exp_val} years."
            if exp_val is not None
            else "No explicit years-of-experience statement found."
        )
    })

    notice_limit = scorecard.get("max_notice")
    notice_match = re.search(
        r'\b(\d{1,3})\s*(?:days?|day notice)\b',
        text
    )

    notice_val = int(notice_match.group(1)) if notice_match else None

    try:
        notice_ok = (
            notice_val is not None
            and notice_limit is not None
            and notice_val <= int(notice_limit)
        )
    except (TypeError, ValueError):
        notice_ok = False

    evidence.append({
        "criterion": "Notice period",
        "matched": notice_ok,
        "quote": (
            f"CV mentions {notice_val} days."
            if notice_val is not None
            else "Notice period not found; recruiter verification required."
        )
    })

    total = len(must) + 2
    score = round(
        ((matched + int(exp_ok) + int(notice_ok)) / total) * 100
    ) if total else 0

    return {
        "score": score,
        "evidence": evidence,
        "method": "transparent_keyword_fallback",
        "caveat": (
            "Fallback matching is approximate. "
            "Verify evidence against the original CV."
        )
    }


def score_cv(cv_text, scorecard):
    """Evaluate a CV using the locally running Ollama model."""
    cv_text = cv_text or ""
    scorecard = scorecard or {}

    base_url = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    ).rstrip("/")

    model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    prompt = {
        "scorecard": scorecard,
        "cv_text": cv_text[:18000],
        "instructions": (
            "Evaluate this CV against the job scorecard. "
            "Use only job-related criteria. Do not use or infer "
            "name, gender, age, photograph, marital status, caste, "
            "religion, disability, or other protected characteristics. "
            "Do not invent qualifications or experience. "
            "Missing evidence must be marked unmatched. "
            "Every evidence quote must be an exact, verbatim substring "
            "from the CV text. Do not recommend automatic rejection. "
            "Return ONLY valid JSON with this structure: "
            '{"score": 0, "evidence": [{"criterion": "Java", '
            '"matched": true, "quote": "exact CV text"}], '
            '"caveat": "Human verification required."}'
        )
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an evidence-grounded recruitment assistant. "
                    "Your scores support human review only."
                )
            },
            {
                "role": "user",
                "content": json.dumps(prompt)
            }
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    try:
        request = urllib.request.Request(
            f"{base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["message"]["content"]
        data = json.loads(content)

        if not isinstance(data.get("evidence"), list):
            raise ValueError("AI returned an invalid evidence format.")

        verified_evidence = []

        for item in data["evidence"]:
            if not isinstance(item, dict):
                continue

            quote = str(item.get("quote", ""))
            verified = bool(quote) and quote in cv_text

            verified_evidence.append({
                "criterion": str(item.get("criterion", "Unspecified")),
                "matched": bool(item.get("matched", False)) and verified,
                "quote": (
                    quote[:260]
                    if verified
                    else "Evidence could not be verified in the extracted CV text."
                )
            })

        score = max(0, min(100, float(data.get("score", 0))))

        return {
            "score": round(score),
            "evidence": verified_evidence,
            "method": "ollama_local",
            "caveat": (
                "Locally generated AI assessment. "
                "Recruiter must verify evidence against the original CV. "
                "This score must not be used for automatic rejection."
            )
        }

    except Exception as error:
        fallback = keyword_score(cv_text, scorecard)
        fallback["caveat"] = (
            "Local AI was unavailable or returned an invalid response. "
            "Transparent keyword fallback used. "
            f"Details: {str(error)[:200]}"
        )
        return fallback
