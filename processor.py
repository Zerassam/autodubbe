"""
Transcription -> Translation -> TTS -> Sync -> Merge
This implementation uses Whisper (local CLI), LibreTranslate public endpoint, gTTS, and ffmpeg.
"""
import os
import subprocess
import json
import logging
from pathlib import Path
import requests
from gtts import gTTS
from utils import ensure_dir

TMP = '/tmp/autodubber'
ensure_dir(TMP)


def extract_audio(video_path, out_wav):
    cmd = ['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', out_wav]
    subprocess.check_call(cmd)


def whisper_transcribe_get_srt(audio_path):
    logging.info('Running whisper for %s', audio_path)
    cmd = ['whisper', audio_path, '--model', 'small', '--output_format', 'srt', '--output_dir', TMP]
    subprocess.check_call(cmd)
    srt_file = str(Path(TMP) / (Path(audio_path).stem + '.srt'))
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
    headers = {'Content-Type': 'application/json'}
    for seg in segments:
        payload = {'q': seg['text'], 'source': 'en', 'target': target, 'format': 'text'}
        r = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        if r.ok:
            seg['text_ar'] = r.json().get('translatedText')
        else:
            logging.error('Translation failed for: %s', seg['text'])
            seg['text_ar'] = seg['text']
    return segments


def tts_segments_and_sync(segments, voice_prefix='tts_seg'):
    files = []
    for i,seg in enumerate(segments):
        text = seg.get('text_ar') or seg['text']
        if not text.strip():
            seg['tts_path'] = None
            continue
        out_mp3 = str(Path(TMP) / f"{voice_prefix}_{i}.mp3")
        tts = gTTS(text=text, lang='ar')
        tts.save(out_mp3)
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
        subprocess.check_call(cmd_tempo)
        seg['tts_path'] = out_fixed
        files.append(out_fixed)
    return segments


def build_full_dub_audio(segments, out_audio_path):
    import wave
    total_dur = max([s['end'] for s in segments])
    silent = str(Path(TMP)/'silent_{}.wav'.format(int(total_dur)))
    cmd = ['ffmpeg','-y','-f','lavfi','-i', f'anullsrc=channel_layout=mono:sample_rate=16000', '-t', str(total_dur), silent]
    subprocess.check_call(cmd)
    concat_files = []
    for s in segments:
        start = s['start']
        if s.get('tts_path'):
            pre = str(Path(TMP)/f'pre_{int(start*1000)}.wav')
            cmd_pre = ['ffmpeg','-y','-f','lavfi','-i', f'anullsrc=channel_layout=mono:sample_rate=16000', '-t', str(start), pre]
            subprocess.check_call(cmd_pre)
            conv = str(Path(TMP)/f'conv_{int(start*1000)}.wav')
            cmd_conv = ['ffmpeg','-y','-i', s['tts_path'], conv]
            subprocess.check_call(cmd_conv)
            concat_files.append(pre)
            concat_files.append(conv)
    trailing = str(Path(TMP)/'trailing.wav')
    cmd_trail = ['ffmpeg','-y','-f','lavfi','-i', f'anullsrc=channel_layout=mono:sample_rate=16000', '-t', '0.5', trailing]
    subprocess.check_call(cmd_trail)
    concat_list = str(Path(TMP)/'concat_list.txt')
    with open(concat_list, 'w', encoding='utf-8') as f:
        for fname in concat_files:
            f.write(f"file '{fname}'\n")
        f.write(f"file '{trailing}'\n")
    cmd_concat = ['ffmpeg','-y','-f','concat','-safe','0','-i', concat_list, '-c','copy', out_audio_path]
    subprocess.check_call(cmd_concat)
    return out_audio_path


def mix_dub_over_video(orig_video, dub_audio, out_video, original_audio_reduce=0.15):
    cmd = ['ffmpeg','-y','-i', orig_video, '-i', dub_audio,
           '-filter_complex', f"[0:a]volume={original_audio_reduce}[a0];[a0][1:a]amix=inputs=2:dropout_transition=0", '-c:v', 'copy', out_video]
    subprocess.check_call(cmd)


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
