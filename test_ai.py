from dotenv import load_dotenv
load_dotenv()

import os
from app.scoring import score_cv

if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: API key not loaded.")
    raise SystemExit(1)

cv_text = """
Java Developer with 3 years of experience.
Worked with Java, Spring Boot, MySQL and REST APIs.
Available with 30 days notice.
"""

scorecard = {
    "must_have": ["Java", "Spring Boot", "MySQL", "REST APIs"],
    "min_experience": 2,
    "max_notice": 60
}

result = score_cv(cv_text, scorecard)

print("\nAI TEST RESULT")
print("--------------------")
print("Method:", result.get("method"))
print("Score:", result.get("score"))
print("Evidence:", result.get("evidence"))
print("Caveat:", result.get("caveat"))