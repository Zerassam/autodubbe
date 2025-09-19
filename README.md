# Project: AutoDubber (YouTube CC -> Arabic Dub pipeline)
# Repository layout in this single file: each file section starts with
# ===== FILE: <path/filename> =====

===== FILE: README.md =====
# AutoDubber

Automated pipeline that: watches a source YouTube channel for Creative Commons videos, downloads each video one-by-one, transcribes with Whisper (local or API), translates segments to Arabic, generates synchronized Arabic voice-over (gTTS by default), merges dub into the original video using ffmpeg, uploads the final video to your YouTube channel, then cleans temporary files.

This project is designed to run with minimal paid services; defaults use open-source/free tools. You *must* respect copyright and only process videos under permissive license (Creative Commons / Public Domain).

## System Requirements

- Python 3.8+
- FFmpeg
- yt-dlp
- OpenAI Whisper
- 2GB+ RAM (for video processing)
- 5GB+ free disk space (temporary files)

## Contents
- `pipeline_main.py` - main loop and queue worker
- `watcher.py` - polls YouTube channel and enqueues new CC videos
- `driver.py` - checks license & downloads videos via yt-dlp and uploads temporary files to Drive if desired
- `processor.py` - transcription (Whisper), translation (LibreTranslate), TTS (gTTS), timing sync & merge (ffmpeg)
- `uploader.py` - YouTube upload helper (OAuth2 interactive flow)
- `utils.py` - helpers (logging, file utils, config loader)
- `setup.py` - setup script for checking dependencies and initial configuration
- `requirements.txt` - Python dependencies
- `config.example.json` - example configuration file
- `Dockerfile` & `docker-compose.yml` - containerized deployment

## Quick Start

### 1. System Dependencies
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg python3-pip python3-venv

# macOS
brew install ffmpeg python

# Install yt-dlp and whisper
pip install yt-dlp openai-whisper
```

### 2. Python Setup
```bash
# Clone and setup
git clone <your-repo>
cd AutoDubber
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run setup script
python setup.py
```

### 3. Google APIs Setup
   - Create a Google Cloud project, enable Drive API if you want Drive features.
   - Create OAuth 2.0 Client Credentials for YouTube Data API v3 (download `client_secrets.json`).
   - For Drive automated uploads, you can use a Service Account and share a folder with it.
   - Get a YouTube Data API key for video metadata

### 4. Configuration
```bash
# Copy example config
cp config/config.example.json config/config.json
# Edit config.json with your settings
### 5. Run
```bash
python pipeline_main.py
```

## Docker Deployment
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f autodubber
```
```
## Notes
- The pipeline processes videos sequentially and deletes temporary files after upload to keep storage usage small.
- Test with a single known CC video first.
- Monitor logs/ directory for detailed processing information.
- The system respects YouTube API rate limits and video licensing.