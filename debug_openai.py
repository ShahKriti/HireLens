from dotenv import load_dotenv
load_dotenv()

import os
from openai import OpenAI

key = os.getenv("OPENAI_API_KEY")

print("API key loaded:", bool(key))
print("API key format:", key.startswith("sk-") if key else False)

try:
    client = OpenAI(api_key=key)

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "user", "content": "Reply with the word SUCCESS"}
        ],
        max_tokens=20
    )

    print("API CONNECTION SUCCESSFUL")
    print("Response:", response.choices[0].message.content)

except Exception as e:
    print("API CONNECTION FAILED")
    print("Error type:", type(e).__name__)
    print("Error message:", str(e))