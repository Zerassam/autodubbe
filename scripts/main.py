import os
import json
from pytube import YouTube
import whisper
from deep_translator import GoogleTranslator
from moviepy.editor import VideoFileClip, AudioFileClip
from gtts import gTTS

# --- تحميل الإعدادات ---
def load_config():
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_path, "config", "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- تحميل الفيديو ---
def download_video(url, output_dir, max_length):
    yt = YouTube(url)
    if yt.length > max_length * 60:
        raise Exception(f"⛔ الفيديو أطول من {max_length} دقيقة!")
    stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
    out_file = stream.download(output_path=output_dir)
    print(f"✅ تم تنزيل الفيديو: {out_file}")
    return out_file

# --- استخراج الصوت ---
def extract_audio(video_path, temp_dir):
    audio_path = os.path.join(temp_dir, "audio.mp3")
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path)
    print(f"🎵 تم استخراج الصوت: {audio_path}")
    return audio_path

# --- تحويل الصوت إلى نص (Whisper) ---
def transcribe_audio(audio_path, source_lang):
    model = whisper.load_model("small")
    result = model.transcribe(audio_path, language=source_lang)
    print("📝 تم تحويل الصوت إلى نص.")
    return result["text"]

# --- ترجمة النص ---
def translate_text(text, target_lang):
    translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
    print("🌍 تم ترجمة النص.")
    return translated

# --- توليد صوت جديد ---
def synthesize_speech(text, target_lang, temp_dir):
    tts = gTTS(text=text, lang=target_lang)
    dub_path = os.path.join(temp_dir, "dub.mp3")
    tts.save(dub_path)
    print("🔊 تم إنشاء ملف الصوت المدبلج.")
    return dub_path

# --- دمج الصوت مع الفيديو ---
def merge_audio_video(video_path, new_audio_path, output_path):
    video = VideoFileClip(video_path)
    new_audio = AudioFileClip(new_audio_path)
    final = video.set_audio(new_audio)
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    print(f"🎬 تم حفظ الفيديو النهائي: {output_path}")

# --- البرنامج الرئيسي ---
def main():
    config = load_config()
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    input_dir = os.path.join(base_path, "input")
    output_dir = os.path.join(base_path, "output")
    temp_dir = os.path.join(base_path, "temp")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    youtube_url = config.get("youtube_url", "")
    if not youtube_url:
        print("⚠️ لم يتم تحديد رابط فيديو في config.json")
        return
    
    # 1. تحميل الفيديو
    video_path = download_video(youtube_url, input_dir, config["max_video_length_minutes"])
    
    # 2. استخراج الصوت
    audio_path = extract_audio(video_path, temp_dir)
    
    # 3. تحويل إلى نص
    text = transcribe_audio(audio_path, config["language_source"])
    
    # 4. ترجمة النص
    translated_text = translate_text(text, config["language_target"])
    
    # 5. توليد صوت مترجم
    dub_audio = synthesize_speech(translated_text, config["language_target"], temp_dir)
    
    # 6. دمج الصوت الجديد مع الفيديو
    output_path = os.path.join(output_dir, f"dubbed.{config['output_format']}")
    merge_audio_video(video_path, dub_audio, output_path)

    # 7. تنظيف الملفات المؤقتة
    if config.get("delete_temp", True):
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        print("🧹 تم مسح الملفات المؤقتة.")

if __name__ == "__main__":
    main()
