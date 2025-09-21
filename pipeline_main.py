import time
import logging
import os
from pathlib import Path
from utils import load_config, setup_logging, ensure_dir
from watcher import poll_channel_and_enqueue, mark_processed
from driver import is_video_cc, download_video, get_video_duration
from processor import process_video_file
from uploader import get_youtube_service, upload_video_to_youtube

cfg = load_config('config.json')
setup_logging()
TMP = cfg.get('TMP_DIR', '/tmp/autodubber')
ensure_dir(TMP)

MAX_DURATION_NORMAL = cfg.get("VIDEO_FILTER", {}).get("MAX_DURATION_NORMAL", 900)
MAX_DURATION_SHORT = cfg.get("VIDEO_FILTER", {}).get("MAX_DURATION_SHORT", 60)
MIN_DURATION = cfg.get("VIDEO_FILTER", {}).get("MIN_DURATION", 5)

IS_SHORT = False  # False للفيديو العادي، True للشورت / الريلز

def cleanup_temp_files(video_id: str, tmp_dir: str):
    try:
        for f in os.listdir(tmp_dir):
            if video_id in f:
                try:
                    os.remove(os.path.join(tmp_dir, f))
                except Exception as e:
                    logging.warning(f"Could not remove {f}: {e}")
        logging.info(f"🧹 Temp files for {video_id} cleaned up.")
    except Exception as e:
        logging.error(f"Cleanup failed for {video_id}: {e}")

def main_loop():
    channel = cfg['SOURCE_CHANNEL_ID']
    yt_service = None

    while True:
        new_vids = poll_channel_and_enqueue(channel)
        if not new_vids:
            logging.info('No new videos. Sleeping...')
            time.sleep(cfg.get('POLL_INTERVAL_SECONDS', 300))
            continue

        for vid in new_vids:
            try:
                ok, meta = is_video_cc(vid)
                if not ok:
                    logging.info('Skipping non-CC video %s', vid)
                    mark_processed(vid)
                    continue

                local_video = download_video(vid, TMP)
                if not local_video:
                    logging.error('Download failed or skipped for %s', vid)
                    mark_processed(vid)
                    continue

                duration = get_video_duration(local_video)
                max_dur = MAX_DURATION_SHORT if IS_SHORT else MAX_DURATION_NORMAL
                if duration > max_dur or duration < MIN_DURATION:
                    logging.info(f"Skipping video {vid}: duration {duration}s outside allowed range.")
                    cleanup_temp_files(Path(local_video).stem, TMP)
                    mark_processed(vid)
                    continue

                final_video = process_video_file(local_video)
                if not final_video:
                    logging.error('Processing failed for %s', vid)
                    cleanup_temp_files(Path(local_video).stem, TMP)
                    mark_processed(vid)
                    continue

                if not yt_service:
                    yt_service = get_youtube_service(
                        cfg['YOUTUBE']['CLIENT_SECRETS_FILE'],
                        cfg['YOUTUBE']['CREDENTIALS_STORE']
                    )

                title = f"[AR] {meta.get('title', '')}"
                desc = f"مترجم ومدبلج آلياً. المصدر: https://www.youtube.com/watch?v={vid} | License: {meta.get('license', 'unknown')}"
                upload_video_to_youtube(yt_service, final_video, title, desc)

                try:
                    os.remove(local_video)
                except:
                    pass
                cleanup_temp_files(Path(local_video).stem, TMP)
                mark_processed(vid)

            except Exception as e:
                logging.exception('Error processing %s: %s', vid, e)

        time.sleep(cfg.get('POLL_INTERVAL_SECONDS', 60))

if __name__ == '__main__':
    main_loop()
