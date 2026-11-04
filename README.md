# SHIV AI — Smart Router & Sovereign Intelligence Server

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Render Free Tier](https://img.shields.io/badge/Render-24%2F7%20Zero--Sleep-46E3B7.svg?logo=render&logoColor=white)](https://render.com)
[![Python 3.11](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![SHIV DB](https://img.shields.io/badge/SHIV_DB-Native_SQLite_WAL-blue.svg)](https://sqlite.org)

High-capacity, fault-tolerant AI Router engineered for continuous 24/7 operation on the Render Free Tier. Built with 50+ pooled API key rotation, leaky-bucket rate limiting, instant failover, native SHIV DB authentication, two-tier persistent memory, and real multimodal engines (FLUX image generation, Edge Neural voice synthesis, and video reels).

---

## 🚀 Key Architectural Pillars

### 1. 50+ API Key Rotation Pool & Instant Failover
- **Leaky-Bucket RPM Tracking**: Monitors per-key request timestamps over sliding 60-second windows.
- **Provider Cascade**: Evaluates requests in priority sequence:
  1. Google Gemini (Gemini 2.0 Flash)
  2. Groq Cloud (Llama 3.3 70B)
  3. Cerebras Cloud (Llama 3.3 70B)
  4. SambaNova Cloud (Llama 3.3 70B)
  5. Mistral AI (Mistral Small)
  6. OpenRouter (Free Tier Models)
  7. Hugging Face Inference
- **Automatic Cooldowns & Circuit Breaker**: Quarantines rate-limited (HTTP 429) keys for 10 minutes and retries automatically when capacity recovers.
- **Zero-Cost Public Fallback**: Automatic public inference fallback ensures 100% server availability even before keys are supplied.

### 2. 24/7 Render Keep-Alive (Zero Sleep)
- Uses Render's free tier (750 free instance hours/month) for continuous zero-cost deployment.
- High-efficiency `/ping` endpoint and built-in background loop keeps the instance active within the 744 hours/month limit.

### 3. Native SHIV DB & Auth Integration
- Direct integration with `shiv_dev.db` using WAL mode and row factory dictionaries.
- **Argon2id & Bcrypt Password Hashing**: Zero mock authentication.
- **HS256 JWT Token Rotation**: Standard access and cryptographic refresh tokens registered in `sessions` table.
- **Two-Tier Memory System**:
  - *Short-Term*: Sliding context window of recent conversational turns.
  - *Long-Term*: User preferences, biographical facts, and project context extracted by heuristic fact learner and stored in `generic_records`.

### 4. Sovereign SHIV AI Identity
- Full abstraction of third-party models. The engine strictly identifies as **SHIV AI** across all conversational turns and multimodal outputs.
- Automated streaming sanitizer strips underlying model watermarks.

### 5. Real Multimodal Synthesis
- **Image Generation**: 1024x1024 synthesis via Pollinations FLUX / Turbo.
- **Voice Synthesis**: Lifelike Microsoft Edge Neural TTS in English (`en-US-ChristopherNeural`, `en-US-JennyNeural`) and Hindi (`hi-IN-MadhurNeural`, `hi-IN-SwaraNeural`).
- **Video Reels**: Frame interpolation with cinematic zoom effects and audio narration.
- **Zero Cloud Storage Cost**: All generated media blobs are stored directly in SQLite `media_files` table and served via `/media/file/{file_name}`.

---

## 📡 API Reference & Endpoints

### Authentication
- `POST /auth/register`: Create user account with Argon2id encryption.
- `POST /auth/login`: Authenticate and receive JWT access + refresh tokens.
- `POST /auth/refresh`: Rotate expired access token using refresh token.
- `POST /auth/logout`: Revoke active session.
- `GET /auth/me`: Retrieve authenticated user profile.

### Inference & Chat (OpenAI Compatible)
- `POST /v1/chat/completions`: Supports standard OpenAI request format with SSE streaming (`stream: true`).

### Multimodal Media
- `POST /media/generate/image`: Generate 1024x1024 image from prompt.
- `POST /media/synthesize/voice`: Synthesize neural audio in MP3 format.
- `POST /media/generate/video`: Generate animated video reel.
- `GET /media/file/{file_name}`: Stream cached media directly from database.

### Two-Tier Memory
- `GET /memory`: Retrieve persistent user facts and preferences.
- `POST /memory`: Manually commit a user preference.
- `DELETE /memory/{record_id}`: Remove a memory record.

### System & Telemetry
- `GET /ping`: Render keep-alive heartbeat.
- `GET /health`: Database connection and provider status.
- `GET /keys/status`: Real-time key pool usage metrics.

---

## 💻 Local Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env

# 3. Start server
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🐳 Docker & Cloud Deployment

```bash
# Build container
docker build -t shivai-router .

# Run container
docker run -p 8000:8000 --env-file .env shivai-router
```
