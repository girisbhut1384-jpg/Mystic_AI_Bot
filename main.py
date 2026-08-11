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
import PIL
from PIL import Image, ImageDraw, ImageFont
try:
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = getattr(Image, 'Resampling', Image).LANCZOS
except:
    pass
# ==========================================

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, 
    CompositeVideoClip, CompositeAudioClip, concatenate_videoclips
)
import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 1. API क्रेडेंशियल्स ---
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

def verify_all_systems():
    print("🔍 सिस्टम्स की जाँच की जा रही है...", flush=True)
    report = "🛠️ <b>सिस्टम हेल्थ रिपोर्ट:</b>\n\n"
    is_youtube_ok = False
    try:
        creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        youtube = build("youtube", "v3", credentials=creds)
        youtube.channels().list(part="id", mine=True).execute()
        report += "✅ <b>YouTube:</b> कनेक्टेड है।\n"
        is_youtube_ok = True
    except: report += "🔴 <b>YouTube:</b> REFRESH_TOKEN एक्सपायर हो गया है!\n"
    send_telegram_report(report)
    return is_youtube_ok

def clean_low_performing_videos():
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
                if stats.get('items') and int(stats['items'][0]['statistics'].get('viewCount', 0)) < 100:
                    youtube.videos().delete(id=vid_id).execute()
                    deleted_count += 1
                    time.sleep(1)
    except: pass

# --- 5. 🚀 अनंत कहानियों का इंजन (Infinite Story Engine) ---
# ये 15 अलग-अलग थीम्स हैं। मशीन हर बार एक नई थीम चुनेगी जिससे कहानी हमेशा अलग होगी।
MYSTERY_CATEGORIES = [
    "Unsolved internet puzzles like Cicada 3301",
    "Real Dark Web crime bust stories",
    "Creepy AI and chatbot incidents",
    "Lost media and mysterious videos found online",
    "Anonymous hacker group biggest attacks",
    "Deep Web horror true stories",
    "Cybersecurity biggest breaches in history",
    "Mysterious websites that suddenly disappeared",
    "Government secret files leaked online",
    "The Mariana Web and quantum computing myths",
    "Computer viruses that destroyed millions",
    "Real stories of digital identity theft",
    "Cryptocurrency billion-dollar heists",
    "Strange coordinates and Google Maps mysteries",
    "Satoshi Nakamoto and the Bitcoin mystery"
]

FALLBACK_SCRIPTS = [
    {
        "title": "सिल्क रोड: इंटरनेट का सबसे खौफनाक बाज़ार! 😱 #shorts",
        "description": "डार्क वेब का असली सच और सिल्क रोड की कहानी। #DarkWebHindi #SilkRoad #InternetMystery",
        "tags": ["DarkWebHindi", "SilkRoad", "InternetMystery", "DeepWebFacts", "shorts"],
        "script": "क्या आपको पता है कि डार्क वेब पर एक ऐसा बाज़ार था, जहाँ दुनिया की हर गैरकानूनी चीज़ घर बैठे मंगवाई जा सकती थी? इसका नाम था सिल्क रोड। इसे इंटरनेट का अंडरवर्ल्ड कहा जाता था। यहाँ ड्रग्स से लेकर हथियारों तक की बोली लगती थी। जब FBI ने इसे पकड़ा, तो जो सच सामने आया उसने पूरी दुनिया को हिला दिया। ऐसे ही खौफनाक रहस्य जानने के लिए चैनल को सब्सक्राइब करें!",
        "captions": ["डार्क वेब का खौफनाक बाज़ार", "घर बैठे मिलती थी हर चीज़", "नाम था सिल्क रोड", "इंटरनेट का अंडरवर्ल्ड", "हथियार और ड्रग्स की बोली", "FBI का खतरनाक छापा", "दुनिया हिल गई", "रहस्य जानने के लिए", "अभी सब्सक्राइब करें"]
    }
]

def get_viral_script():
    print("🧠 AI से बिल्कुल नई और अनोखी कहानी लिखी जा रही है...", flush=True)
    # हर बार एक रैंडम थीम
    theme = random.choice(MYSTERY_CATEGORIES)
    
    # AI को सख़्त निर्देश: "हर बार कुछ नया और रियल लाओ"
    prompt = f"You are a YouTube Shorts Scriptwriter. Generate a highly engaging, factually accurate Hindi script about a UNIQUE, specific real-world event related to: '{theme}'. Rule 1: DO NOT repeat common stories. Pick a lesser-known, true shocking event. Rule 2: First 3 seconds must be a powerful shocking hook. Rule 3: End with a CTA. Return ONLY valid JSON with keys: 'title' (Curiosity question), 'description', 'tags', 'script', 'captions' (array of 10 to 12 very short phrases for fast editing). DO NOT wrap in markdown."
    
    for _ in range(3):
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
            res = requests.get(url, timeout=25)
            content = res.text.replace("```json", "").replace("```", "").strip()
            if "{" in content and "}" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            data = json.loads(content)
            if isinstance(data, dict) and "script" in data and "captions" in data:
                return data
        except: time.sleep(2)
    return random.choice(FALLBACK_SCRIPTS)

# --- 6. 🎧 सस्पेंस वाली आवाज़ (Rate -15%) ---
async def generate_audio(text):
    print("🎙️ सस्पेंस वाली आवाज़ तैयार हो रही है...", flush=True)
    for _ in range(3):
        try:
            communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="-15%")
            await communicate.save("voice.mp3")
            main_audio = AudioFileClip("voice.mp3")
            if os.path.exists("bgm.mp3"):
                try:
                    bg_audio = AudioFileClip("bgm.mp3").volumex(0.12)
                    from moviepy.audio.fx.all import audio_loop
                    bg_audio = audio_loop(bg_audio, duration=main_audio.duration)
                    main_audio = CompositeAudioClip([main_audio, bg_audio])
                except: pass
            return main_audio, main_audio.duration
        except: time.sleep(2)
    raise Exception("आवाज़ जनरेट नहीं हो पाई")

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

def smart_crop_to_916(clip):
    target_ratio = 1080 / 1920
    clip_ratio = clip.w / clip.h
    if clip_ratio > target_ratio:
        clip = clip.resize(height=1920)
        return clip.crop(x_center=clip.w//2, y_center=clip.h//2, width=1080, height=1920)
    else:
        clip = clip.resize(width=1080)
        return clip.crop(x_center=clip.w//2, y_center=clip.h//2, width=1080, height=1920)

# --- 8. 🎥 हज़ारों यूनीक विजुअल्स (4K Quality) ---
# 25+ डार्क और रहस्यमयी कीवर्ड्स ताकि हर वीडियो का बैकग्राउंड अलग हो
TECH_KEYWORDS = [
    "iceberg underwater", "abandoned dark building", "police siren night", 
    "cybercrime investigation", "confidential top secret document", "deep dark ocean", 
    "scary dark room", "computer forensics", "data breach security", 
    "anonymous mask shadow", "binary code glowing", "creepy artificial intelligence",
    "dark web concept", "digital lock security", "government secret files",
    "hacker typing in dark", "scary empty street night", "hidden surveillance camera",
    "creepy old computer", "digital fingerprint scan"
]

def fetch_stock_video(duration, clip_index):
    errors = []
    for attempt in range(5):
        keyword = random.choice(TECH_KEYWORDS)
        video_url = None
        
        try:
            # रैंडम पेज (1 से 5) ताकि एक ही वीडियो बार-बार न आए
            page = random.randint(1, 5)
            url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&per_page=15&page={page}&orientation=portrait"
            res = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=10)
            if res.status_code == 200 and res.json().get("videos"):
                # .sort() चौड़ाई x ऊंचाई (Width * Height) के आधार पर करता है, जिससे हमेशा 4K/HD वीडियो ही मिलता है
                video_url = sorted(random.choice(res.json()["videos"])["video_files"], key=lambda x: x['width'] * x['height'], reverse=True)[0]["link"]
        except Exception as e: errors.append(f"Pexels: {e}")

        if not video_url and PIXABAY_API_KEY:
            try:
                page = random.randint(1, 3)
                pix_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={urllib.parse.quote(keyword)}&per_page=15&page={page}"
                res = requests.get(pix_url, timeout=10)
                if res.status_code == 200 and res.json().get("hits"):
                    video_url = random.choice(res.json()["hits"])["videos"].get("large", random.choice(res.json()["hits"])["videos"].get("medium"))["url"]
            except Exception as e: errors.append(f"Pixabay: {e}")

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
                        repeats = int(duration / clip.duration) + 1
                        clip = concatenate_videoclips([clip] * repeats).subclip(0, duration)
                        
                    clip = smart_crop_to_916(clip)
                    return clip.set_duration(duration)
                except Exception as e:
                    errors.append(f"Crop Error: {e}")
            else:
                errors.append("Download Blocked")

    raise Exception(f"5 कोशिशों के बाद भी असली वीडियो नहीं मिला। मशीन रोक दी गई है ताकि कचरा अपलोड न हो।")

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
    y = int(canvas_h * 0.55) - (bbox[3] - bbox[1]) // 2 
    
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFE81F", stroke_width=15, stroke_fill="#8B0000", align='center')
    
    temp_name = f"cap_{clip_index}_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

def compile_final_video(captions, final_audio, audio_duration):
    print("🎞️ फास्ट-कट 4K एडिटिंग शुरू हो रही है...", flush=True)
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
            
    final_video = concatenate_videoclips(processed_clips, method="compose").set_duration(total_duration)
    padded_audio = CompositeAudioClip([final_audio]).set_duration(total_duration)
    final_video = final_video.set_audio(padded_audio)
    
    final_video.write_videofile("final_viral_shorts.mp4", fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    return "final_viral_shorts.mp4"

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
            send_telegram_report("🚨 <b>मशीन बंद:</b> YouTube टोकन एक्सपायर हो गया है।", is_error=True)
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
        
        send_telegram_report(f"✅ <b>नया शॉर्ट्स लाइव! (Infinite Engine)</b>\n🎬 {safe_title}\n🔗 {video_url}")
        print("🎉 सफलता! 4K वीडियो लाइव हो गया।", flush=True)
        
    except Exception as e:
        error_details = str(traceback.format_exc())
        send_telegram_report(f"🚨 मशीन क्रैश:\n\n{error_details[-1500:]}", is_error=True)
        sys.exit(1)
