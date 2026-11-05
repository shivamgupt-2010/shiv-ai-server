# Multi-stage production container for SHIV AI Smart Router
FROM python:3.11-slim

# Avoid buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=10000

# Install system dependencies including FFmpeg for multimodal video reels
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    libsqlite3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifest
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete project code including .env
COPY . .

# Ensure data directory exists
RUN mkdir -p /app/data /app/data/media

# Expose standard port
EXPOSE 10000

# Run FastAPI with Uvicorn (1 worker to remain well within Render free tier 512MB RAM)
CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
