"""
Probe working model identifiers for Gemini, Groq, and SambaNova.
"""
import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv("F:/SHIV\shivai/.env")

GEMINI_KEY = os.getenv("GEMINI_API_KEYS", "").split(",")[0].strip()
GROQ_KEY = os.getenv("GROQ_API_KEYS", "").split(",")[0].strip()
SAMBANOVA_KEY = os.getenv("SAMBANOVA_API_KEYS", "").split(",")[0].strip()


async def check_gemini_models():
    print("\n--- Checking Gemini Models ---")
    candidates = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro", "gemini-2.5-flash", "gemini-pro"]
    async with httpx.AsyncClient(timeout=15.0) as client:
        for m in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={GEMINI_KEY}"
            payload = {"contents": [{"parts": [{"text": "hi"}]}]}
            try:
                r = await client.post(url, json=payload)
                print(f"  {m}: HTTP {r.status_code}")
                if r.status_code == 200:
                    print(f"    FOUND WORKING MODEL: {m}")
                    break
            except Exception as e:
                print(f"  {m}: {e}")


async def check_groq_models():
    print("\n--- Checking Groq Models ---")
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                models = [m["id"] for m in r.json().get("data", [])]
                print(f"  Available models ({len(models)}): {models[:10]}")
            else:
                print(f"  Failed: {r.status_code} - {r.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")


async def check_sambanova_models():
    print("\n--- Checking SambaNova Models ---")
    url = "https://api.sambanova.ai/v1/models"
    headers = {"Authorization": f"Bearer {SAMBANOVA_KEY}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                models = [m["id"] for m in r.json().get("data", [])]
                print(f"  Available models ({len(models)}): {models[:10]}")
            else:
                print(f"  Failed: {r.status_code} - {r.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")


async def main():
    await check_gemini_models()
    await check_groq_models()
    await check_sambanova_models()

if __name__ == "__main__":
    asyncio.run(main())
