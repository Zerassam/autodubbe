"""
Transcription -> Translation -> TTS -> Sync -> Merge
This implementation uses Whisper (local CLI), LibreTranslate public endpoint, gTTS, and ffmpeg.
"""
import os
import subprocess
import json
import logging
import tempfile
import shutil
from pathlib import Path
import requests
from gtts import gTTS
from utils import ensure_dir

TMP = '/tmp/autodubber'
ensure_dir(TMP)


def extract_audio(video_path, out_wav):
    """Extract audio from video file using ffmpeg"""
    cmd = ['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', out_wav]
    try:
        subprocess.check_call(cmd, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        logging.error(f"Audio extraction failed: {e}")
        raise


def whisper_transcribe_get_srt(audio_path):
    logging.info('Running whisper for %s', audio_path)
    cmd = ['whisper', audio_path, '--model', 'small', '--output_format', 'srt', '--output_dir', TMP]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        logging.error(f"Whisper transcription failed: {e}")
        raise
    srt_file = str(Path(TMP) / (Path(audio_path).stem + '.srt'))
    if not Path(srt_file).exists():
        raise FileNotFoundError(f"SRT file not generated: {srt_file}")
    return srt_file


def parse_srt(srt_path):
    segments = []
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    parts = [p.strip() for p in content.split('\n\n') if p.strip()]
    for part in parts:
        lines = part.split('\n')
        if len(lines) >= 3:
            times = lines[1]
            txt = ' '.join(lines[2:])
            start_s, end_s = times.split(' --> ')
            def ts_to_seconds(t):
                h,m,s = t.split(':')
                s,ms = s.split(',')
                return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0
            segments.append({'start': ts_to_seconds(start_s.strip()), 'end': ts_to_seconds(end_s.strip()), 'text': txt.strip()})
    return segments


def translate_segments(segments, endpoint='https://libretranslate.de/translate', target='ar'):
    """Translate text segments using LibreTranslate API"""
    headers = {'Content-Type': 'application/json'}
    for seg in segments:
        if not seg['text'].strip():
            seg['text_ar'] = seg['text']
            continue
        payload = {'q': seg['text'], 'source': 'en', 'target': target, 'format': 'text'}
        try:
            r = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            if r.ok:
                seg['text_ar'] = r.json().get('translatedText', seg['text'])
            else:
                logging.error('Translation failed for: %s (Status: %d)', seg['text'], r.status_code)
                seg['text_ar'] = seg['text']
        except requests.RequestException as e:
            logging.error('Translation request failed for: %s (%s)', seg['text'], e)
            seg['text_ar'] = seg['text']
    return segments


def tts_segments_and_sync(segments, voice_prefix='tts_seg'):
    """Generate TTS audio for each segment and adjust timing"""
    files = []
    for i,seg in enumerate(segments):
        text = seg.get('text_ar') or seg['text']
        if not text.strip():
            seg['tts_path'] = None
            continue
        out_mp3 = str(Path(TMP) / f"{voice_prefix}_{i}.mp3")
        try:
            tts = gTTS(text=text, lang='ar')
            tts.save(out_mp3)
        except Exception as e:
            logging.error(f"TTS generation failed for segment {i}: {e}")
            seg['tts_path'] = None
            continue
            
        target_dur = seg['end'] - seg['start']
        cmd_probe = ['ffprobe','-v','error','-select_streams','a:0',
                     '-show_entries','stream=duration','-of','default=noprint_wrappers=1:nokey=1', out_mp3]
        try:
            out = subprocess.check_output(cmd_probe).decode().strip()
            tts_dur = float(out)
        except Exception:
            tts_dur = target_dur
        speed = tts_dur / target_dur if target_dur>0.01 else 1.0
        atempo = max(0.5, min(1.0/speed if speed!=0 else 1.0, 2.0))
        out_fixed = str(Path(TMP) / f"{voice_prefix}_{i}_fixed.mp3")
        cmd_tempo = ['ffmpeg','-y','-i', out_mp3, '-filter:a', f"atempo={atempo}", out_fixed]
        try:
            subprocess.check_call(cmd_tempo, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            logging.error(f"Audio tempo adjustment failed for segment {i}: {e}")
            seg['tts_path'] = out_mp3  # Use original if tempo adjustment fails
            files.append(out_mp3)
            continue
        seg['tts_path'] = out_fixed
        files.append(out_fixed)
    return segments


def build_full_dub_audio(segments, out_audio_path):
    """Build complete dubbed audio track with proper timing."""
    if not segments:
        return None
        
    # Create silence for the full duration
    total_dur = max([s['end'] for s in segments]) if segments else 10
    temp_files = []
    
    # Create base silence
    silence_file = str(Path(TMP) / 'base_silence.wav')
    cmd_silence = ['ffmpeg', '-y', '-f', 'lavfi', '-i', 
                   f'anullsrc=channel_layout=mono:sample_rate=22050', 
                   '-t', str(total_dur + 1), silence_file]
    try:
        subprocess.check_call(cmd_silence, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to create silence track: {e}")
        return None
    temp_files.append(silence_file)
    
    # Overlay each TTS segment at the correct time
    current_input = silence_file
    for s in segments:
        if not s.get('tts_path') or not os.path.exists(s['tts_path']):
            continue
            
        # Create output for this overlay
        next_output = str(Path(TMP) / f'overlay_{len(temp_files)}.wav')
        
        # Overlay TTS at the correct timestamp
        cmd_overlay = ['ffmpeg', '-y', '-i', current_input, '-i', s['tts_path'],
                      '-filter_complex', f'[1:a]adelay={int(s["start"]*1000)}|{int(s["start"]*1000)}[delayed];[0:a][delayed]amix=inputs=2:dropout_transition=0',
                      next_output]
        try:
            subprocess.check_call(cmd_overlay, stderr=subprocess.DEVNULL)
            temp_files.append(next_output)
            current_input = next_output
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to overlay segment: {e}")
            continue
    
    # Copy final result to output path
    if current_input != silence_file:
        shutil.copy2(current_input, out_audio_path)
    else:
        shutil.copy2(silence_file, out_audio_path)
    
    # Cleanup temp files
    for f in temp_files:
        try:
            os.remove(f)
        except:
            pass
            
    return out_audio_path


def mix_dub_over_video(orig_video, dub_audio, out_video, original_audio_reduce=0.15):
    """Mix dubbed audio with original video, reducing original audio volume"""
    cmd = ['ffmpeg','-y','-i', orig_video, '-i', dub_audio,
           '-filter_complex', f"[0:a]volume={original_audio_reduce}[a0];[a0][1:a]amix=inputs=2:dropout_transition=0", '-c:v', 'copy', out_video]
    try:
        subprocess.check_call(cmd, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        logging.error(f"Video mixing failed: {e}")
        raise


def process_video_file(local_video_path):
    """
    end-to-end processing for one local video file
    returns the path to the processed video
    """
    base = Path(local_video_path).stem
    audio_wav = str(Path(TMP)/f'{base}.wav')
    extract_audio(local_video_path, audio_wav)
    srt = whisper_transcribe_get_srt(audio_wav)
    segments = parse_srt(srt)
    segments = translate_segments(segments)
    segments = tts_segments_and_sync(segments)
    dub_audio = str(Path(TMP)/f'{base}_dub.mp3')
    build_full_dub_audio(segments, dub_audio)
    out_video = str(Path(TMP)/f'{base}_ar_dub.mp4')
    mix_dub_over_video(local_video_path, dub_audio, out_video)
    return out_video
