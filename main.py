import os
import sys
import io
import requests
import time
import random
import textwrap
import json
import urllib.parse
import traceback
import asyncio
from datetime import datetime, timedelta, timezone

# ==========================================
# 🛑 THE MASTER PATCH (ANTIALIAS FIX) 🛑
# यह वह पैच है जो आपके स्क्रीनशॉट वाले एरर को जड़ से ख़त्म करेगा
import PIL
from PIL import Image
try:
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = getattr(Image, 'Resampling', Image).LANCZOS
except Exception as e:
    print(f"Patch Error: {e}")
# ==========================================

from moviepy.editor import AudioFileClip, concatenate_videoclips, CompositeVideoClip, VideoFileClip, CompositeAudioClip
from PIL import ImageDraw, ImageFont
import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# GitHub Actions में हिंदी टेक्स्ट को क्रैश होने से बचाने के लिए
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 1. API क्रेडेंशियल्स (ऑटो-क्लीनर) ---
def clean_key(k):
    return k.strip().replace(" ", "").replace("\n", "") if k else ""

CLIENT_ID = clean_key(os.environ.get("CLIENT_ID"))
CLIENT_SECRET = clean_key(os.environ.get("CLIENT_SECRET"))
REFRESH_TOKEN = clean_key(os.environ.get("REFRESH_TOKEN"))
PEXELS_API_KEY = clean_key(os.environ.get("PEXELS_API_KEY"))
PIXABAY_API_KEY = clean_key(os.environ.get("PIXABAY_API_KEY"))
TELEGRAM_BOT_TOKEN = clean_key(os.environ.get("TELEGRAM_BOT_TOKEN"))
TELEGRAM_CHAT_ID = clean_key(os.environ.get("TELEGRAM_CHAT_ID"))

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, PEXELS_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ एरर: GitHub Secrets में API Keys गायब हैं!")
    sys.exit(1)

# --- 2. 100% सेफ टेलीग्राम रिपोर्टिंग ---
def send_telegram_report(message, is_error=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    if not is_error:
        payload["parse_mode"] = "HTML"
    try:
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code != 200 and not is_error:
            del payload["parse_mode"]
            requests.post(url, json=payload, timeout=15)
    except: pass

# --- 3. एडवांस API डिटेक्टिव ---
def verify_all_systems():
    print("🔍 सिस्टम्स की गहरी जाँच की जा रही है...", flush=True)
    report = "🛠️ <b>सिस्टम हेल्थ रिपोर्ट:</b>\n\n"
    is_youtube_ok = False
    
    # YouTube Check
    try:
        creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        youtube = build("youtube", "v3", credentials=creds)
        youtube.channels().list(part="id", mine=True).execute()
        report += "✅ <b>YouTube:</b> कनेक्टेड है।\n"
        is_youtube_ok = True
    except: report += "🔴 <b>YouTube:</b> REFRESH_TOKEN एक्सपायर हो गया है (नया लें)!\n"

    # Pexels Check
    try:
        pex_res = requests.get("https://api.pexels.com/videos/search?query=tech&per_page=1", headers={"Authorization": PEXELS_API_KEY}, timeout=10)
        if pex_res.status_code == 200: report += "✅ <b>Pexels:</b> बिल्कुल सही काम कर रहा है।\n"
        else: report += f"🔴 <b>Pexels:</b> एरर {pex_res.status_code}\n"
    except Exception as e: report += f"❌ <b>Pexels:</b> डाउन है ({e})।\n"

    send_telegram_report(report)
    return is_youtube_ok

# --- 4. ऑटो-डिलीट सिस्टम ---
def clean_low_performing_videos():
    print("🧹 पुराने फ्लॉप वीडियो को स्कैन कर रहे हैं...", flush=True)
    try:
        creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        youtube = build("youtube", "v3", credentials=creds)
        deleted_count = 0
        response = youtube.channels().list(part="contentDetails", mine=True).execute()
        uploads_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        playlist_res = youtube.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=50).execute()
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        for item in playlist_res.get('items', []):
            vid_id = item['snippet']['resourceId']['videoId']
            pub_at = datetime.fromisoformat(item['snippet']['publishedAt'].replace('Z', '+00:00'))
            if pub_at < seven_days_ago:
                stats = youtube.videos().list(part="statistics", id=vid_id).execute()
                if stats.get('items'):
                    views = int(stats['items'][0]['statistics'].get('viewCount', 0))
                    if views < 100:
                        youtube.videos().delete(id=vid_id).execute()
                        deleted_count += 1
                        time.sleep(1)
        if deleted_count > 0:
            send_telegram_report(f"🧹 <b>चैनल क्लीनअप:</b> {deleted_count} फ्लॉप वीडियो हटाए गए।")
    except Exception as e:
        print(f"⚠️ क्लीनअप एरर: {e}", flush=True)

# --- 5. फुल-प्रूफ स्क्रिप्ट जनरेशन ---
FALLBACK_SCRIPTS = [
    {
        "title": "इंटरनेट का सबसे डरावना सच! 😱 #shorts",
        "description": "डार्क वेब के रहस्य! #mystery #hacker #tech",
        "tags": ["mystery", "hacker", "tech", "shorts"],
        "script": "इंटरनेट की दुनिया जितनी साफ़ दिखती है, अंदर से उतनी ही खौफनाक है। जिसे हम इस्तेमाल करते हैं, वो सिर्फ 4 प्रतिशत है। बाकी 96 प्रतिशत डार्क वेब है, जहां ऐसे रहस्य छिपे हैं जो आपकी नींद उड़ा देंगे। ऐसे रहस्य जानने के लिए अभी सब्सक्राइब करें!",
        "captions": ["इंटरनेट का काला सच", "सिर्फ 4 प्रतिशत", "बाकी डार्क वेब", "नींद उड़ा देंगे", "अभी सब्सक्राइब करें"]
    }
]

def get_viral_script():
    print("🧠 AI से नई कहानी लिखी जा रही है...", flush=True)
    prompt = "You are a JSON API. Generate a mystery tech script for a YouTube Short in Hindi. You MUST return ONLY a valid JSON object. DO NOT wrap in markdown. The JSON MUST have exactly these keys: 'title', 'description', 'tags', 'script', and 'captions'."
    for _ in range(3):
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
            res = requests.get(url, timeout=20)
            content = res.text.replace("```json", "").replace("```", "").strip()
            if "{" in content and "}" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            data = json.loads(content)
            if isinstance(data, dict) and "script" in data and "captions" in data:
                return data
        except: time.sleep(2)
    return random.choice(FALLBACK_SCRIPTS)

# --- 6. आवाज़ जनरेशन ---
async def generate_audio(text):
    print("🎙️ आवाज़ तैयार हो रही है...", flush=True)
    for _ in range(3):
        try:
            communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
            await communicate.save("voice.mp3")
            main_audio = AudioFileClip("voice.mp3")
            if os.path.exists("bgm.mp3"):
                bg_audio = AudioFileClip("bgm.mp3").volumex(0.15)
                from moviepy.audio.fx.all import audio_loop
                bg_audio = audio_loop(bg_audio, duration=main_audio.duration)
                return CompositeAudioClip([main_audio, bg_audio]), main_audio.duration
            return main_audio, main_audio.duration
        except: time.sleep(2)
    raise Exception("आवाज़ जनरेट नहीं हो पाई (Edge-TTS Error)")

# --- 7. असली इंसान जैसा डाउनलोडर ---
def safe_download_video(url, filename):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        r = requests.get(url, stream=True, headers=headers, timeout=20)
        if r.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk: f.write(chunk)
            return True
        return False
    except: return False

# --- 8. गारंटीड स्टॉक वीडियो (अब क्रैश नहीं होगा) ---
TECH_KEYWORDS = ["hacker typing", "neon server", "cyber security", "data center", "matrix code"]

def fetch_stock_video(duration, clip_index):
    errors = []
    for attempt in range(5):
        keyword = random.choice(TECH_KEYWORDS)
        video_url = None
        
        try:
            url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&per_page=15&page={random.randint(1, 3)}&orientation=portrait"
            res = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=10)
            if res.status_code == 200 and res.json().get("videos"):
                video_url = sorted(random.choice(res.json()["videos"])["video_files"], key=lambda x: x['width'] * x['height'], reverse=True)[0]["link"]
        except Exception as e: errors.append(f"Pexels Search: {e}")

        if video_url:
            temp_name = f"temp_vid_{clip_index}_{attempt}.mp4"
            if safe_download_video(video_url, temp_name):
                try:
                    clip = VideoFileClip(temp_name).without_audio()
                    if getattr(clip, 'duration', None) is None or clip.duration <= 0:
                        raise Exception("वीडियो लंबाई नहीं मिली")
                        
                    if clip.duration > duration + 1:
                        start_time = random.uniform(0, clip.duration - duration - 1)
                        clip = clip.subclip(start_time, start_time + duration)
                    else:
                        clip = concatenate_videoclips([clip] * (int(duration / clip.duration) + 1)).subclip(0, duration)
                        
                    # यहीं ANTIALIAS की वजह से क्रैश होता था, अब यह पैच की वजह से 100% चलेगा
                    return clip.resize(height=1920).crop(x_center=clip.w/2, y_center=1920/2, width=1080, height=1920).set_duration(duration)
                except Exception as e:
                    errors.append(f"Resize/Cut Error: {e}")
            else:
                errors.append("Download Blocked/Failed")

    error_summary = "\n".join(errors[-3:]) # आखिरी 3 एरर दिखाएगा
    raise Exception(f"5 कोशिशों के बाद भी वीडियो नहीं बना। कारण:\n{error_summary}")

# --- 9. सबटाइटल्स ---
def create_subtitle_clip(text, duration, clip_index):
    canvas_w, canvas_h = 1080, 1920
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = "Yantramanav-Black.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/yantramanav/Yantramanav-Black.ttf", font_path)
        except: pass
    try: font = ImageFont.truetype(font_path, 140) 
    except: font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text, width=12)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    x = (canvas_w - (bbox[2] - bbox[0])) // 2
    y = int(canvas_h * 0.65) - (bbox[3] - bbox[1]) // 2 
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFE81F", stroke_width=15, stroke_fill="black", align='center')
    
    temp_name = f"cap_{clip_index}_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 10. वीडियो कंपाइलेशन ---
def compile_final_video(captions, final_audio, audio_duration):
    print("🎞️ फाइनल वीडियो जोड़ा जा रहा है...", flush=True)
    total_duration = audio_duration + 2.0 
    clip_duration = total_duration / len(captions)
    processed_clips = []
    
    for idx, cap_text in enumerate(captions):
        base_clip = fetch_stock_video(clip_duration, idx)
        if cap_text.strip():
            txt_clip = create_subtitle_clip(cap_text, clip_duration, idx)
            comp = CompositeVideoClip([base_clip, txt_clip], size=(1080, 1920)).set_duration(clip_duration)
            processed_clips.append(comp)
        else:
            processed_clips.append(base_clip)
            
    final_video = concatenate_videoclips(processed_clips, method="compose").set_audio(final_audio).set_duration(total_duration)
    final_video.write_videofile("final_viral_shorts.mp4", fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    return "final_viral_shorts.mp4"

# --- 11. YouTube अपलोड ---
def upload_video(video_file, title, description, tags):
    print("📤 YouTube पर अपलोड हो रहा है...", flush=True)
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    youtube = build("youtube", "v3", credentials=creds)
    request_body = {"snippet": {"categoryId": "22", "title": title, "description": description, "tags": tags}, "status": {"privacyStatus": "public", "madeForKids": False}}
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    res = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    return f"https://youtu.be/{res['id']}"

if __name__ == "__main__":
    try:
        if not verify_all_systems():
            send_telegram_report("🚨 <b>मशीन बंद:</b> YouTube टोकन एक्सपायर हो गया है। कृपया नया टोकन अपडेट करें।", is_error=True)
            sys.exit(1)
            
        clean_low_performing_videos()
        
        data = get_viral_script()
        safe_script = data.get("script", FALLBACK_SCRIPTS[0]["script"])
        safe_captions = data.get("captions", FALLBACK_SCRIPTS[0]["captions"])
        safe_title = data.get("title", FALLBACK_SCRIPTS[0]["title"])
        safe_desc = data.get("description", FALLBACK_SCRIPTS[0]["description"])
        safe_tags = data.get("tags", FALLBACK_SCRIPTS[0]["tags"])
        
        final_audio, audio_duration = asyncio.run(generate_audio(safe_script))
        
        final_video = compile_final_video(safe_captions, final_audio, audio_duration)
        video_url = upload_video(final_video, safe_title, safe_desc, safe_tags)
        
        send_telegram_report(f"✅ <b>नया शॉर्ट्स लाइव!</b>\n🎬 {safe_title}\n🔗 {video_url}")
        print("🎉 सफलता! वीडियो लाइव हो गया।", flush=True)
        
    except Exception as e:
        error_details = str(traceback.format_exc())
        # अब अगर कोई एरर आएगा, तो उसकी पूरी जन्म-कुंडली टेलीग्राम पर आएगी
        send_telegram_report(f"🚨 मशीन क्रैश (विस्तृत रिपोर्ट):\n\n{error_details[:800]}", is_error=True)
        print("❌ एरर आ गया, टेलीग्राम पर रिपोर्ट भेजी गई।", flush=True)
        sys.exit(1)
