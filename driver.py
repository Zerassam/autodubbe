"""
Responsible for checking license and downloading videos (only CC/Public) using yt-dlp.
Supports distinction between normal videos (<= 15min) and shorts (<= 60s).
Supports optional cookies file for age-restricted or bot-protected videos.
"""
import subprocess
import json
import logging
import requests
import isodate
import cv2
from pathlib import Path
from utils import ensure_dir, load_config
import os

cfg = load_config('config.json')
TMP = cfg.get('TMP_DIR', '/tmp/autodubber')
ensure_dir(TMP)

API_KEY = cfg["YOUTUBE"].get("API_KEY")

# الخيار الافتراضي: ملف الكوكيز في مجلد config
DEFAULT_COOKIES_FILE = Path('config') / 'cookies.txt'

# السماح بالاستبدال بواسطة متغير البيئة
COOKIES_FILE = Path(os.environ.get("YOUTUBE_COOKIES_FILE", DEFAULT_COOKIES_FILE))

COOKIES_FILE = os.environ.get("YOUTUBE_COOKIES_FILE")  # <-- مسار الكوكيز من .env

# حدود الطول
MAX_NORMAL = cfg.get("VIDEO_FILTER", {}).get("MAX_DURATION_NORMAL", 900)   # 15 دقيقة
MAX_SHORT = cfg.get("VIDEO_FILTER", {}).get("MAX_DURATION_SHORT", 60)     # 60 ثانية
MIN_DUR = cfg.get("VIDEO_FILTER", {}).get("MIN_DURATION", 5)


def is_video_cc(video_id):
    """يتأكد أن الفيديو Creative Commons أو Public Domain"""
    cmd = ['yt-dlp', '--dump-json', f'https://www.youtube.com/watch?v={video_id}']
    if COOKIES_FILE:
        cmd.insert(1, f'--cookies={COOKIES_FILE}')
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
    """جلب مدة الفيديو بالثواني من YouTube Data API"""
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


def get_video_duration(video_path):
    """جلب مدة الفيديو بالثواني عبر ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return float(result.decode().strip())
    except Exception as e:
        logging.error(f"Could not get duration for {video_path}: {e}")
        return 0


def is_short_format(video_path):
    """يتحقق إن كان الفيديو عمودي (short) باستخدام OpenCV"""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        cap.release()
        return height > width  # إذا الارتفاع أكبر => عمودي => Short
    except Exception as e:
        logging.warning(f"Could not determine format of {video_path}: {e}")
        return False


def download_video(video_id, out_dir=TMP):
    """تحميل الفيديو بعد التحقق من نوعه (short/normal)"""
    # التحقق من الطول عبر API
    dur = get_video_duration_api(video_id)
    if dur is not None:
        if dur < MIN_DUR:
            logging.info("Skipping %s: too short (%.1fs)", video_id, dur)
            return None
        if dur > MAX_NORMAL:  # إذا تجاوز 15 دقيقة يرفض مباشرة
            logging.info("Skipping %s: too long (%.1fs)", video_id, dur)
            return None

    # تحميل الفيديو
    out_template = str(Path(out_dir) / f"{video_id}.%(ext)s")
    cmd = ['yt-dlp', '-f', 'bestvideo+bestaudio/best', '-o', out_template]
    if COOKIES_FILE:
        cmd.append(f'--cookies={COOKIES_FILE}')
    cmd.append(f'https://www.youtube.com/watch?v={video_id}')

    logging.info('Downloading %s ...', video_id)
    subprocess.check_call(cmd)

    # العثور على الملف الناتج
    p = Path(out_dir)
    for f in p.glob(f'{video_id}.*'):
        if f.suffix.lower() in ['.mp4', '.mkv', '.webm']:
            # تحقق إن كان Short
            if dur is not None and dur <= MAX_SHORT:
                logging.info("%s detected as SHORT (%.1fs)", video_id, dur)
            else:
                logging.info("%s detected as NORMAL video (%.1fs)", video_id, dur if dur else 0)
            return str(f)
    return None
