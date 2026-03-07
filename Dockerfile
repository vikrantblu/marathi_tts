# ─── Marathi TTS Web ─────────────────────────────────────────────────────────
# Multi-stage build: slim Python image + only production deps
# Usage:
#   docker build -t marathi-tts-web .
#   docker run -p 8000:8000 marathi-tts-web

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for audio/OCR processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-mar \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY marathi_tts_web/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy web application
COPY marathi_tts_web/ /app/

# Collect static files
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "marathi_tts.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "120"]
