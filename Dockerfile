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
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
RUN pip install -r /app/requirements.txt

# Copy project files
COPY . /app

# Create necessary directories
RUN mkdir -p /app/logs /app/input /app/output /tmp/autodubber

ENV TMP_DIR=/tmp/autodubber
VOLUME ["/tmp/autodubber", "/app/logs", "/app/config"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "pipeline_main.py"]