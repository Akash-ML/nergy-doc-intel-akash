import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq
from backend.config import settings

def main():
    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": "Say hello in exactly 5 words."}]
    )
    print(f"✅ Groq connection success.")
    print(f"Response: {response.choices[0].message.content}")

if __name__ == "__main__":
    main()
