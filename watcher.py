"""
Improved watcher: polls a YouTube channel (channel id or URL) and returns new video IDs to process.
Supports /channel/, /c/, /user/ URL forms and fixes prior missing imports.
Uses yt-dlp --flat-playlist + --dump-json to fetch uploads metadata.
"""
import subprocess
import json
import logging
from pathlib import Path
from utils import ensure_dir

PROCESSED_STORE = 'processed_videos.json'


def load_processed():
    p = Path(PROCESSED_STORE)
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text(encoding='utf-8')))
    except Exception:
        return set()


def save_processed(s):
    p = Path(PROCESSED_STORE)
    p.write_text(json.dumps(list(s)), encoding='utf-8')


def poll_channel_and_enqueue(channel_url_or_id, limit=10):
    """Return list of video ids (strings) to process. Accepts a channel id or a channel URL.
    Tries common URL patterns until it finds uploads.
    """
    logging.info(f'Polling channel {channel_url_or_id}')
    candidates = []
    if str(channel_url_or_id).startswith('http'):
        candidates.append(channel_url_or_id)
    else:
        # try common YouTube URL patterns
        candidates.append(f'https://www.youtube.com/channel/{channel_url_or_id}')
        candidates.append(f'https://www.youtube.com/c/{channel_url_or_id}')
        candidates.append(f'https://www.youtube.com/user/{channel_url_or_id}')

    vids = []
    for url in candidates:
        cmd = ['yt-dlp', '--flat-playlist', '--dump-json', url]
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            logging.debug('yt-dlp failed for candidate URL: %s', url)
            continue
        for line in out.splitlines():
            try:
                meta = json.loads(line.decode('utf-8'))
                vid = meta.get('id')
                if vid:
                    vids.append(vid)
            except Exception:
                continue
        if vids:
            break

    processed = load_processed()
    new = [v for v in vids if v not in processed]
    return new[:limit]


def mark_processed(vid):
    s = load_processed()
    s.add(vid)
    save_processed(s)