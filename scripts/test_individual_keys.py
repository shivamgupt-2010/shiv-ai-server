"""
Diagnostic script to test each of the 5 connected API keys individually.
"""
import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv("F:/SHIV/shivai/.env")

GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEYS", "").split(",") if k.strip()]
SAMBANOVA_KEYS = [k.strip() for k in os.getenv("SAMBANOVA_API_KEYS", "").split(",") if k.strip()]
MISTRAL_KEYS = [k.strip() for k in os.getenv("MISTRAL_API_KEYS", "").split(",") if k.strip()]

TIMEOUT = 30.0


async def test_gemini(key: str, idx: int):
    print(f"\n[Testing Gemini Key #{idx}] (Key prefix: {key[:12]}...)")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": "Say 'Gemini OK' and nothing else."}]}]
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
            print(f"  HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                print(f"  SUCCESS! Reply: {text.strip()}")
                return True
            else:
                print(f"  FAILED: {resp.text[:300]}")
                return False
        except Exception as e:
            print(f"  ERROR: {e}")
            return False


async def test_groq(key: str):
    print(f"\n[Testing Groq Key] (Key prefix: {key[:12]}...)")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "Say 'Groq OK' and nothing else."}],
        "max_tokens": 20,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            print(f"  HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                print(f"  SUCCESS! Reply: {text.strip()}")
                return True
            else:
                print(f"  FAILED: {resp.text[:300]}")
                return False
        except Exception as e:
            print(f"  ERROR: {e}")
            return False


async def test_sambanova(key: str):
    print(f"\n[Testing SambaNova Key] (Key prefix: {key[:12]}...)")
    url = "https://api.sambanova.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": "Meta-Llama-3.3-70B-Instruct",
        "messages": [{"role": "user", "content": "Say 'SambaNova OK' and nothing else."}],
        "max_tokens": 20,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            print(f"  HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                print(f"  SUCCESS! Reply: {text.strip()}")
                return True
            else:
                print(f"  FAILED: {resp.text[:300]}")
                return False
        except Exception as e:
            print(f"  ERROR: {e}")
            return False


async def test_mistral(key: str):
    print(f"\n[Testing Mistral Key] (Key prefix: {key[:12]}...)")
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": "mistral-small-latest",
        "messages": [{"role": "user", "content": "Say 'Mistral OK' and nothing else."}],
        "max_tokens": 20,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            print(f"  HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                print(f"  SUCCESS! Reply: {text.strip()}")
                return True
            else:
                print(f"  FAILED: {resp.text[:300]}")
                return False
        except Exception as e:
            print(f"  ERROR: {e}")
            return False


async def main():
    print("=" * 60)
    print("TESTING 5 CONNECTED SHIV AI PROVIDER KEYS")
    print("=" * 60)

    results = {}

    for idx, k in enumerate(GEMINI_KEYS, 1):
        res = await test_gemini(k, idx)
        results[f"Gemini Key #{idx}"] = res

    for k in GROQ_KEYS:
        res = await test_groq(k)
        results["Groq Key"] = res

    for k in SAMBANOVA_KEYS:
        res = await test_sambanova(k)
        results["SambaNova Key"] = res

    for k in MISTRAL_KEYS:
        res = await test_mistral(k)
        results["Mistral Key"] = res

    print("\n" + "=" * 60)
    print("SUMMARY RESULTS:")
    for name, ok in results.items():
        status_str = "ACTIVE / OPERATIONAL" if ok else "FAILED / NEEDS REVIEW"
        print(f"  - {name}: {status_str}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
