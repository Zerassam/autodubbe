# Dockerfile for AutoDubber
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio --no-deps
RUN pip install -r /app/requirements.txt

# Copy project files
COPY . /app

# Create necessary directories
RUN mkdir -p /app/logs /app/input /app/output /tmp/autodubber /app/config

ENV TMP_DIR=/tmp/autodubber
ENV YOUTUBE_COOKIES_FILE=/app/config/youtube_cookies.txt
VOLUME ["/tmp/autodubber", "/app/logs", "/app/config"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "pipeline_main.py"]
