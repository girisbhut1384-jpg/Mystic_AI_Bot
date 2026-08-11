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

# हिंदी टेक्स्ट को क्रैश होने से बचाने के लिए
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 1. API क्रेडेंशियल्स (सख्त सफाई) ---
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

# --- 2. 🧹 फ्लॉप वीडियो क्लीनर (ऑटो-डिलीट सिस्टम) ---
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
                if stats.get('items') and int(stats['items'][0]['statistics'].get('viewCount', 0)) < 100:
                    youtube.videos().delete(id=vid_id).execute()
                    deleted_count += 1
                    time.sleep(1)
        if deleted_count > 0:
            send_telegram_report(f"🧹 <b>चैनल क्लीनअप:</b> {deleted_count} फ्लॉप वीडियो हटाए गए।")
    except: pass

# --- 3. 🚀 अनंत कहानियों का इंजन (15 Categories) ---
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
        "description": "डार्क वेब का असली सच। #DarkWebHindi #SilkRoad #InternetMystery",
        "tags": ["DarkWebHindi", "SilkRoad", "InternetMystery", "DeepWebFacts", "shorts"],
        "script": "डार्क वेब पर एक ऐसा बाज़ार था, जहाँ दुनिया की हर गैरकानूनी चीज़ घर बैठे मंगवाई जा सकती थी। इसका नाम था सिल्क रोड! जब FBI ने यहाँ छापा मारा, तो दुनिया हिल गई। क्योंकि इस खौफनाक काले साम्राज्य का मालिक कोई बड़ा डॉन नहीं, बल्कि रॉस उलब्रिच्ट नाम का एक आम सा दिखने वाला लड़का था! ऐसे ही असली रहस्य जानने के लिए चैनल सब्सक्राइब करें!",
        "scenes": [
            {"caption": "डार्क वेब का खौफनाक बाज़ार", "search_query": "hacker computer dark room"},
            {"caption": "मिलती थी हर गैरकानूनी चीज़", "search_query": "secret confidential files document"},
            {"caption": "नाम था सिल्क रोड", "search_query": "dark web deep ocean iceberg"},
            {"caption": "FBI का खतरनाक छापा", "search_query": "police siren flashing lights night"},
            {"caption": "दुनिया हिल गई!", "search_query": "shocked person looking at screen"},
            {"caption": "मालिक कोई डॉन नहीं...", "search_query": "hacker taking off mask"},
            {"caption": "आम सा लड़का रॉस था!", "search_query": "arrested criminal police"},
            {"caption": "असली रहस्य जानने के लिए", "search_query": "cyber security lock"},
            {"caption": "अभी सब्सक्राइब करें", "search_query": "subscribe button tech"}
        ]
    }
]

def get_viral_script():
    print("🧠 AI से नई, सटीक और हज़ारों यूनीक कहानियों में से एक लिखी जा रही है...", flush=True)
    selected_theme = random.choice(MYSTERY_CATEGORIES)
    
    prompt = f"You are a YouTube Shorts Scriptwriter. Write a highly engaging, factually accurate Hindi script about a UNIQUE real-world event related to: '{selected_theme}'. Rule 1: First 3 seconds must be a powerful shocking hook. Rule 2: NEVER leave a mystery incomplete. Provide the real conclusion. Rule 3: Return ONLY valid JSON with keys: 'title' (Clickbait question), 'description', 'tags', 'script', and 'scenes'. Rule 4: 'scenes' MUST be an array of objects. Each object must have 'caption' (short Hindi text) and 'search_query' (highly specific English search term for Pexels, e.g., 'police siren night'). DO NOT wrap in markdown."
    
    for _ in range(3):
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
            res = requests.get(url, timeout=25)
            content = res.text.replace("```json", "").replace("```", "").strip()
            if "{" in content and "}" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            data = json.loads(content)
            
            if "captions" in data and "scenes" not in data:
                data["scenes"] = [{"caption": c, "search_query": "cyber crime mystery"} for c in data["captions"]]
                
            if isinstance(data, dict) and "script" in data and "scenes" in data:
                return data
        except: time.sleep(2)
    
    return random.choice(FALLBACK_SCRIPTS)

# --- 4. 🎧 भारी, सीरियस और थ्रिलर आवाज़ (Pitch -5Hz, Rate -15%) ---
async def generate_audio(text):
    print("🎙️ थ्रिलर जैसी सस्पेंस वाली आवाज़ तैयार हो रही है...", flush=True)
    for _ in range(3):
        try:
            communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="-15%", pitch="-5Hz")
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

# --- 5. 🎥 4K विजुअल्स + 25 बैकअप कीवर्ड्स (Varieties) ---
TECH_KEYWORDS = [
    "iceberg underwater", "abandoned dark building", "police siren night", 
    "cybercrime investigation", "confidential top secret document", "deep dark ocean", 
    "scary dark room", "computer forensics", "data breach security", 
    "anonymous mask shadow", "binary code glowing", "creepy artificial intelligence",
    "dark web concept", "digital lock security", "government secret files",
    "hacker typing in dark", "scary empty street night", "hidden surveillance camera",
    "creepy old computer", "digital fingerprint scan", "matrix green code",
    "server room blinking lights", "dark web browser", "hacker arrest", "cyber attack map"
]

def fetch_stock_video(duration, clip_index, search_query):
    errors = []
    print(f"🔍 सीन {clip_index} के लिए ढूँढ रहे हैं: '{search_query}'", flush=True)
    
    # अगर AI का कीवर्ड फेल हो जाए, तो हमारी 25 कीवर्ड्स की डिक्शनरी से रैंडम डार्क वीडियो लेगा
    keywords_to_try = [search_query, search_query.split(" ")[0], random.choice(TECH_KEYWORDS), random.choice(TECH_KEYWORDS)]
    
    for keyword in keywords_to_try:
        for attempt in range(2):
            video_url = None
            try:
                page = random.randint(1, 3)
                url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&per_page=15&page={page}&orientation=portrait"
                res = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=10)
                if res.status_code == 200 and res.json().get("videos"):
                    # 4K/HD क्वालिटी की 100% गारंटी (Highest resolution first)
                    video_url = sorted(random.choice(res.json()["videos"])["video_files"], key=lambda x: x['width'] * x['height'], reverse=True)[0]["link"]
            except Exception as e: errors.append(f"Pexels: {e}")

            if not video_url and PIXABAY_API_KEY:
                try:
                    pix_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={urllib.parse.quote(keyword)}&per_page=10"
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
    raise Exception("सटीक वीडियो नहीं मिल पाया।")

# --- 6. डायनामिक और हाईलाइटेड कैप्शंस ---
def create_subtitle_clip(text, duration, clip_index):
    canvas_w, canvas_h = 1080, 1920
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = "Yantramanav-Black.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/yantramanav/Yantramanav-Black.ttf", font_path)
        except: pass
    try: font = ImageFont.truetype(font_path, 150) 
    except: font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text, width=15)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    x = (canvas_w - (bbox[2] - bbox[0])) // 2
    y = int(canvas_h * 0.55) - (bbox[3] - bbox[1]) // 2 
    
    # पीला टेक्स्ट और गाढ़ा लाल स्ट्रोक ताकि स्क्रीन पर एकदम पॉप-अप हो
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFE81F", stroke_width=18, stroke_fill="#660000", align='center')
    
    temp_name = f"cap_{clip_index}_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 7. वीडियो कंपाइलेशन ---
def compile_final_video(scenes, final_audio, audio_duration):
    print("🎞️ सीन-बाय-सीन 4K एडिटिंग शुरू हो रही है...", flush=True)
    total_duration = audio_duration + 2.0 
    clip_duration = total_duration / len(scenes) 
    processed_clips = []
    
    for idx, scene in enumerate(scenes):
        cap_text = scene.get("caption", "")
        search_query = scene.get("search_query", "hacker dark mystery")
        
        base_clip = fetch_stock_video(clip_duration, idx, search_query)
        
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
            send_telegram_report("🚨 <b>मशीन बंद:</b> YouTube टोकन एक्सपायर हो गया है। कृपया नया टोकन अपडेट करें।", is_error=True)
            sys.exit(1)
            
        clean_low_performing_videos()
        
        data = get_viral_script()
        safe_script = data.get("script", FALLBACK_SCRIPTS[0]["script"])
        safe_scenes = data.get("scenes", FALLBACK_SCRIPTS[0]["scenes"])
        safe_title = data.get("title", FALLBACK_SCRIPTS[0]["title"])
        safe_desc = data.get("description", FALLBACK_SCRIPTS[0]["description"])
        safe_tags = data.get("tags", FALLBACK_SCRIPTS[0]["tags"])
        
        final_audio, audio_duration = asyncio.run(generate_audio(safe_script))
        final_video = compile_final_video(safe_scenes, final_audio, audio_duration)
        video_url = upload_video(final_video, safe_title, safe_desc, safe_tags)
        
        send_telegram_report(f"✅ <b>नया शॉर्ट्स लाइव! (Ultimate Infinite Engine)</b>\n🎬 {safe_title}\n🔗 {video_url}")
        print("🎉 सफलता! 4K वीडियो लाइव हो गया।", flush=True)
        
    except Exception as e:
        error_details = str(traceback.format_exc())
        send_telegram_report(f"🚨 मशीन क्रैश:\n\n{error_details[-1500:]}", is_error=True)
        sys.exit(1)
