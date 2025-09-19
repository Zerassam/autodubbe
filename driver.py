"""
Responsible for checking license and downloading videos (only CC/Public) using yt-dlp.
Also checks video duration via YouTube Data API (API_KEY) before downloading.
"""
import subprocess
import json
import logging
import requests
import isodate
from pathlib import Path
from utils import ensure_dir, load_config

cfg = load_config('config.json')
TMP = cfg.get('TMP_DIR', '/tmp/autodubber')
ensure_dir(TMP)

API_KEY = cfg["YOUTUBE"].get("API_KEY")
MAX_DUR = cfg.get("VIDEO_FILTER", {}).get("MAX_DURATION_SECONDS", 60)
MIN_DUR = cfg.get("VIDEO_FILTER", {}).get("MIN_DURATION_SECONDS", 5)


def is_video_cc(video_id):
    cmd = ['yt-dlp', '--dump-json', f'https://www.youtube.com/watch?v={video_id}']
    try:
        out = subprocess.check_output(cmd)
        meta = json.loads(out)
    except Exception as e:
        logging.error('yt-dlp dump-json failed for %s: %s', video_id, e)
        return False, None

    license_field = meta.get('license', '') or ''
    license_field = license_field.lower()
    is_cc = ('creative commons' in license_field) or ('public domain' in license_field)
    return is_cc, meta


def get_video_duration_api(video_id):
    """Check video duration in seconds using YouTube Data API v3."""
    if not API_KEY:
        logging.warning("API_KEY not set. Duration check skipped.")
        return None
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"id": video_id, "part": "contentDetails", "key": API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        items = data.get("items", [])
        if not items:
            logging.error("Video %s not found in API response.", video_id)
            return None
        duration_str = items[0]["contentDetails"]["duration"]
        duration = isodate.parse_duration(duration_str).total_seconds()
        return duration
    except Exception as e:
        logging.error("API duration check failed for %s: %s", video_id, e)
        return None


def download_video(video_id, out_dir=TMP):
    # تحقق من طول الفيديو قبل التحميل
    dur = get_video_duration_api(video_id)
    if dur is not None:
        if dur > MAX_DUR or dur < MIN_DUR:
            logging.info("Skipping %s: duration %.1fs outside allowed range.", video_id, dur)
            return None

    out_template = str(Path(out_dir) / f"{video_id}.%(ext)s")
    cmd = ['yt-dlp', '-f', 'bestvideo+bestaudio/best', '-o', out_template,
           f'https://www.youtube.com/watch?v={video_id}']
    logging.info('Downloading %s ...', video_id)
    subprocess.check_call(cmd)

    # العثور على الملف الناتج
    p = Path(out_dir)
    for f in p.glob(f'{video_id}.*'):
        if f.suffix.lower() in ['.mp4', '.mkv', '.webm']:
            return str(f)
    return None
