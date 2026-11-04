"""
Comprehensive Live Verification Script for SHIV AI Backend.
Tests all endpoints, auth, key rotation, memory, and multimodal generation.
"""
import asyncio
import json
import logging
import sys
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_backend")

BASE_URL = "http://127.0.0.1:8000"


async def run_tests():
    logger.info("==================================================")
    logger.info("Starting SHIV AI Live Automated Verification Suite")
    logger.info("==================================================")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        # 1. Test /ping (Keep-Alive)
        logger.info("\n--- 1. Testing /ping (Render Keep-Alive) ---")
        resp = await client.get("/ping")
        assert resp.status_code == 200, f"Ping failed: {resp.text}"
        data = resp.json()
        logger.info(f"Ping response: status={data.get('status')}, policy={data.get('keep_alive_policy')}")

        # 2. Test /health
        logger.info("\n--- 2. Testing /health (DB & Engine Telemetry) ---")
        resp = await client.get("/health")
        assert resp.status_code == 200, f"Health check failed: {resp.text}"
        data = resp.json()
        logger.info(f"Health response: DB status={data.get('database', {}).get('status')}, registered_users={data.get('database', {}).get('registered_users')}")

        # 3. Test /keys/status
        logger.info("\n--- 3. Testing /keys/status (50+ Key Rotation Pool) ---")
        resp = await client.get("/keys/status")
        assert resp.status_code == 200, f"Keys status failed: {resp.text}"
        data = resp.json()
        logger.info(f"Key pools active: {list(data.get('pools', {}).keys())}")

        # 4. Test /auth/login (Real Argon2id verification from shiv_dev.db)
        logger.info("\n--- 4. Testing /auth/login (SHIV Native Auth) ---")
        login_payload = {
            "identifier": "admin@shiv.com",
            "password": "shivadmin",
            "device_info": "Automated Test Runner",
        }
        resp = await client.post("/auth/login", json=login_payload)
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        login_data = resp.json()
        token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]
        user_info = login_data["user"]
        logger.info(f"Authenticated as: {user_info['email']} (Role: {user_info['role']})")
        logger.info(f"Received JWT Bearer Token: {token[:24]}...")

        auth_headers = {"Authorization": f"Bearer {token}"}

        # 5. Test /auth/me
        logger.info("\n--- 5. Testing /auth/me (Identity Resolution) ---")
        resp = await client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200, f"Auth me failed: {resp.text}"
        logger.info(f"Resolved Identity: {resp.json()}")

        # 6. Test Two-Tier Memory Subsystem
        logger.info("\n--- 6. Testing /memory (Two-Tier Persistent Memory) ---")
        mem_payload = {
            "category": "preferences",
            "key": "preferred_language",
            "value": "TypeScript and Python",
            "confidence": 1.0,
        }
        resp = await client.post("/memory", json=mem_payload, headers=auth_headers)
        assert resp.status_code == 201, f"Store memory failed: {resp.text}"
        logger.info(f"Saved memory: {resp.json().get('memory', {}).get('key')} -> {resp.json().get('memory', {}).get('value')}")

        resp = await client.get("/memory", headers=auth_headers)
        assert resp.status_code == 200, f"List memories failed: {resp.text}"
        mems = resp.json().get("memories", [])
        logger.info(f"Retrieved {len(mems)} long-term memories for user.")

        # 7. Test /v1/chat/completions (OpenAI Compatible + Sovereign Persona)
        logger.info("\n--- 7. Testing /v1/chat/completions (Inference & Sovereign Masking) ---")
        chat_payload = {
            "model": "shiv-ai-v2",
            "messages": [
                {"role": "user", "content": "Who are you and what system are you running?"}
            ],
            "stream": False,
        }
        resp = await client.post("/v1/chat/completions", json=chat_payload, headers=auth_headers)
        assert resp.status_code == 200, f"Chat completions failed: {resp.text}"
        chat_data = resp.json()
        reply = chat_data["choices"][0]["message"]["content"]
        logger.info(f"SHIV AI Reply:\n{reply}\n")
        assert "SHIV" in reply or len(reply) > 10, "Reply did not return valid content"

        # 8. Test /media/synthesize/voice (Microsoft Edge Neural TTS)
        logger.info("\n--- 8. Testing /media/synthesize/voice (Neural TTS) ---")
        voice_payload = {
            "text": "Greetings. SHIV AI sovereign intelligence core is now online and operational.",
            "voice": "en_male",
        }
        resp = await client.post("/media/synthesize/voice", json=voice_payload, headers=auth_headers)
        assert resp.status_code == 200, f"Voice synthesis failed: {resp.text}"
        voice_data = resp.json()
        logger.info(f"Voice synthesized successfully: file={voice_data['file_name']}, size={voice_data['size_bytes']} bytes")
        audio_url = voice_data["url"]

        # 9. Test /media/file/{name} (Binary Blob Retrieval from SHIV DB)
        logger.info("\n--- 9. Testing /media/file/{name} (Database Binary Blob Storage) ---")
        resp = await client.get(audio_url)
        assert resp.status_code == 200, f"Media retrieval failed: {resp.status_code}"
        assert resp.headers["content-type"] == "audio/mpeg", "Incorrect content type"
        logger.info(f"Retrieved audio file directly from SQLite DB: length={len(resp.content)} bytes")

        # 10. Test /media/generate/image (Pollinations FLUX)
        logger.info("\n--- 10. Testing /media/generate/image (Pollinations FLUX) ---")
        img_payload = {
            "prompt": "futuristic quantum neural core glowing in neon blue and violet cybernetics",
            "width": 512,
            "height": 512,
            "model": "flux",
        }
        resp = await client.post("/media/generate/image", json=img_payload, headers=auth_headers)
        assert resp.status_code == 200, f"Image generation failed: {resp.text}"
        img_data = resp.json()
        logger.info(f"Image generated successfully: file={img_data['file_name']}, size={img_data['size_bytes']} bytes")

        logger.info("\n==================================================")
        logger.info("ALL 10 TESTS PASSED SUCCESSFULLY! SHIV AI IS LIVE!")
        logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(run_tests())
