# Project: AutoDubber (YouTube CC -> Arabic Dub pipeline)
# Repository layout in this single file: each file section starts with
# ===== FILE: <path/filename> =====

===== FILE: README.md =====
# AutoDubber

Automated pipeline that: watches a source YouTube channel for Creative Commons videos, downloads each video one-by-one, transcribes with Whisper (local or API), translates segments to Arabic, generates synchronized Arabic voice-over (gTTS by default), merges dub into the original video using ffmpeg, uploads the final video to your YouTube channel, then cleans temporary files.

This project is designed to run with minimal paid services; defaults use open-source/free tools. You *must* respect copyright and only process videos under permissive license (Creative Commons / Public Domain).

## Contents
- `pipeline_main.py` - main loop and queue worker
- `watcher.py` - polls YouTube channel and enqueues new CC videos
- `driver.py` - checks license & downloads videos via yt-dlp and uploads temporary files to Drive if desired
- `processor.py` - transcription (Whisper), translation (LibreTranslate), TTS (gTTS), timing sync & merge (ffmpeg)
- `uploader.py` - YouTube upload helper (OAuth2 interactive flow)
- `utils.py` - helpers (logging, file utils, config loader)
- `requirements.txt` - Python dependencies
- `config.example.json` - example configuration file
- `systemd/autodubber.service` - optional systemd unit example

## Quickstart (high-level)
1. Create Python virtualenv and install dependencies: `pip install -r requirements.txt`.
2. Install system dependencies: `yt-dlp`, `ffmpeg`, Whisper (local) if you plan to use it locally.
3. Prepare Google APIs:
   - Create a Google Cloud project, enable Drive API if you want Drive features.
   - Create OAuth 2.0 Client Credentials for YouTube Data API v3 (download `client_secrets.json`).
   - For Drive automated uploads, you can use a Service Account and share a folder with it.
4. Copy `config.example.json` → `config.json` and fill values (channel id, drive folder ids, paths,...)
5. Run `python pipeline_main.py` to start the worker loop.

## Notes
- The pipeline processes videos sequentially and deletes temporary files after upload to keep storage usage small.
- Test with a single known CC video first.