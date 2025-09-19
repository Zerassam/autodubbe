"""
Responsible for checking license and downloading videos (only CC/Public) using yt-dlp.
Also optional uploading of the original to Drive (if configured).
"""
import subprocess
import json
import logging
from pathlib import Path
from utils import ensure_dir

TMP = '/tmp/autodubber'
ensure_dir(TMP)


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


def download_video(video_id, out_dir=TMP):
    out_template = str(Path(out_dir) / f"{video_id}.%(ext)s")
    cmd = ['yt-dlp', '-f', 'bestvideo+bestaudio/best', '-o', out_template, f'https://www.youtube.com/watch?v={video_id}']
    logging.info('Downloading %s ...', video_id)
    subprocess.check_call(cmd)
    # find file
    p = Path(out_dir)
    for f in p.glob(f'{video_id}.*'):
        if f.suffix.lower() in ['.mp4', '.mkv', '.webm']:
            return str(f)
    return None