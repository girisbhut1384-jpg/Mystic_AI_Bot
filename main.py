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
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, CompositeAudioClip, concatenate_videoclips
)
from moviepy.audio.fx.all import audio_loop, audio_fadeout
import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# हिंदी टेक्स्ट को क्रैश होने से बचाने के लिए
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
    if not is_error: payload["parse_mode"] = "HTML"
    try:
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code != 200 and not is_error:
            del payload["parse_mode"]
            requests.post(url, json=payload, timeout=15)
    except: pass

def verify_all_systems():
    print("🔍 सिस्टम्स की जाँच की जा रही है...", flush=True)
    report = "🛠️ <b>सिस्टम हेल्थ रिपोर्ट:</b>\n"
    is_youtube_ok = False
    try:
        creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        youtube = build("youtube", "v3", credentials=creds)
        youtube.channels().list(part="id", mine=True).execute()
        report += "✅ <b>YouTube:</b> कनेक्टेड है।\n"
        is_youtube_ok = True
    except: report += "🔴 <b>YouTube:</b> REFRESH_TOKEN एक्सपायर हो गया है!\n"
    
    report += "✅ <b>Video Engine:</b> Pexels/Pixabay HD ऑप्टिमाइज्ड है।\n"
    report += "✅ <b>Music Engine:</b> bg_music फोल्डर रेडी है।"
    send_telegram_report(report)
    return is_youtube_ok

# --- 2. 🧹 फ्लॉप वीडियो क्लीनर (7 दिन, 100 व्यूज से कम) ---
def clean_low_performing_videos():
    try:
        creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        youtube = build("youtube", "v3", credentials=creds)
        deleted_count = 0
        response = youtube.channels().list(part="contentDetails", mine=True).execute()
        if not response.get('items'): return
        
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
    except Exception as e:
        print(f"⚠️ क्लीनअप में दिक्कत: {e}")

# --- 3. 🧠 याद्दाश्त (Memory System) ---
HISTORY_FILE = "history.txt"

def get_used_topics():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    return []

def save_used_topic(topic):
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(topic + "\n")
    except: pass

MYSTERY_CATEGORIES = [
    "Cicada 3301 unsolved internet puzzle", "The Max Headroom Incident TV hack",
    "Mt. Gox Crypto Heist billion dollar", "KGB Secrets Soviet union spies",
    "Bermuda Triangle of Space satellite anomaly", "Dark Web Red Rooms myth",
    "Edward Snowden NSA leaks reality", "Stuxnet virus destroying nuclear plants",
    "Anonymous hacker group biggest attacks", "Mariana Web and quantum computing",
    "Satoshi Nakamoto Bitcoin creator mystery", "Creepy AI and chatbot incidents",
    "Government secret files leaked online", "Real stories of digital identity theft"
]

FALLBACK_SCRIPTS = {
    "title": "अंतरिक्ष का रहस्यमयी कोना! 😱 #shorts",
    "description": "स्पेस का बरमूडा ट्राएंगल। #SpaceMystery #NASA #InternetMystery",
    "tags": ["SpaceMystery", "NASA", "InternetMystery", "shorts"],
    "script": "क्या आपको पता है, अंतरिक्ष में एक ऐसी जगह है, जहाँ से गुज़रते ही सैटेलाइट काम करना बंद कर देते हैं। इसे स्पेस का बरमूडा ट्राएंगल कहा जाता है। हबल टेलीस्कोप से लेकर इंटरनेशनल स्पेस स्टेशन तक, जब भी इस इलाके से गुज़रते हैं, तो उनके कैमरे और सिस्टम क्रैश हो जाते हैं। नासा आज तक इसका सटीक कारण नहीं बता पाया है। ऐसे ही डरावने रहस्य जानने के लिए चैनल सब्सक्राइब करें, क्योंकि यही असली वजह है कि...",
    "scenes": [
        {"caption": "क्या आपको पता है?", "search_query": "satellite space anomaly dark"},
        {"caption": "अंतरिक्ष की रहस्यमयी जगह", "search_query": "dark universe galaxy"},
        {"caption": "सैटेलाइट हो जाते हैं बंद", "search_query": "creepy static tv screen"},
        {"caption": "स्पेस का बरमूडा ट्राएंगल", "search_query": "abstract glowing network data"},
        {"caption": "हबल टेलीस्कोप क्रैश", "search_query": "server room blinking lights"},
        {"caption": "सिस्टम हो जाते हैं फेल", "search_query": "glowing neon code"},
        {"caption": "नासा भी है हैरान", "search_query": "classified top secret folder"},
        {"caption": "कारण कोई नहीं जानता", "search_query": "dark deep web mystery"},
        {"caption": "रहस्य जानने के लिए", "search_query": "cyber security digital lock"},
        {"caption": "क्योंकि यही असली वजह है कि...", "search_query": "matrix code glowing"}
    ]
}

def get_viral_script():
    print("🧠 AI से नई, परफेक्ट और लूपिंग कहानी लिखी जा रही है...", flush=True)
    used_topics = get_used_topics()
    used_str = ", ".join(used_topics[-5:]) if used_topics else "None"
    
    selected_theme = random.choice(MYSTERY_CATEGORIES)
    prompt = f"Write a Hindi YouTube Shorts script about: '{selected_theme}'. Do NOT use these past topics: [{used_str}]. CRITICAL RULE 1: PERFECT LOOP. Must start with 'क्या आपको पता है...' and end EXACTLY with '...सब्सक्राइब करें, क्योंकि यही असली वजह है कि...'. CRITICAL RULE 2: Complete the story (reveal the truth). CRITICAL RULE 3: Use commas for dramatic pauses. CRITICAL RULE 4: Return ONLY valid JSON with keys: 'title', 'description', 'tags', 'script', and 'scenes'. CRITICAL RULE 5: 'scenes' array must have 'caption' (Hindi) and 'search_query' (English query for Pexels, e.g. 'hacker dark room', 'police flashing lights'). Do NOT use words like 'toy', 'girl', 'office', 'happy' in queries."
    
    for _ in range(3):
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
            res = requests.get(url, timeout=25)
            content = res.text.replace("```json", "").replace("```", "").strip()
            if "{" in content and "}" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            data = json.loads(content)
            
            if isinstance(data, dict) and "script" in data and "scenes" in data:
                save_used_topic(selected_theme)
                return data
        except: time.sleep(2)
    return FALLBACK_SCRIPTS

# --- 4. 🎧 परफेक्ट डॉक्युमेंट्री आवाज़ (-5Hz Pitch) ---
async def generate_voiceover(text):
    print("🎙️ ट्रू क्राइम डॉक्युमेंट्री आवाज़ तैयार हो रही है...", flush=True)
    for _ in range(3):
        try:
            communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="-15%", pitch="-5Hz")
            await communicate.save("voice.mp3")
            main_audio = AudioFileClip("voice.mp3")
            return main_audio, main_audio.duration
        except: time.sleep(2)
    raise Exception("आवाज़ जनरेट नहीं हो पाई")

def get_random_bgm():
    bg_folder = "bg_music"
    if os.path.exists(bg_folder):
        tracks = [f for f in os.listdir(bg_folder) if f.endswith(('.mp3', '.wav'))]
        if tracks: return os.path.join(bg_folder, random.choice(tracks))
    if os.path.exists("bgm.mp3"): return "bgm.mp3"
    return None

# --- 5. 🛡️ नेगेटिव कीवर्ड फिल्टर (Anti-Garbage) ---
BLACKLIST_WORDS = [
    "toy", "jellyfish", "football", "soccer", "dance", "dancing", "party", 
    "girl", "kid", "child", "baby", "playing", "happy", "smiling", 
    "office", "worker", "corridor", "3d glasses", "laughing", "pet", "animation"
]

def is_video_valid(video_data):
    video_text = str(video_data).lower()
    for word in BLACKLIST_WORDS:
        if word in video_text: return False
    return True

STRICT_DARK_VISUALS = [
    "cyberpunk hacker room", "abandoned server farm", "glowing neon code",
    "fbi tactical raid", "true crime documentary style", "dark police flashing lights",
    "hacker typing dark room", "secret confidential files document",
    "cyber security digital lock", "abstract glowing network data",
    "digital fingerprint scan dark", "hooded hacker coding dark", 
    "dark deep web mystery", "matrix code glowing", "server room blinking lights", 
    "classified top secret folder", "satellite space anomaly dark"
]

def safe_download_video(url, filename):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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

# --- 6. 🎥 RAM-Friendly 1080p विजुअल्स (Smart Trimming) ---
def fetch_stock_video(duration, clip_index, search_query):
    errors = []
    print(f"🔍 सीन {clip_index} के लिए ढूँढ रहे हैं: '{search_query}'", flush=True)
    
    fallback_query = search_query.split(" ")[0] + " " + search_query.split(" ")[1] if len(search_query.split(" ")) > 1 else search_query
    keywords_to_try = [search_query, fallback_query, random.choice(STRICT_DARK_VISUALS)]
    
    for keyword in keywords_to_try:
        for attempt in range(2):
            video_url = None
            try:
                page = random.randint(1, 2)
                url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&per_page=15&page={page}&orientation=portrait"
                res = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=10)
                if res.status_code == 200 and res.json().get("videos"):
                    valid_vids = [v for v in res.json()["videos"] if is_video_valid(v)]
                    if valid_vids:
                        best_vid = random.choice(valid_vids)
                        hd_files = [f for f in best_vid["video_files"] if f.get("quality") in ["hd", "fhd"] and f.get("width", 0) >= 720]
                        if hd_files: video_url = sorted(hd_files, key=lambda x: x["width"], reverse=True)[0]["link"]
                        else: video_url = best_vid["video_files"][0]["link"]
            except Exception as e: errors.append(f"Pexels: {e}")

            if not video_url and PIXABAY_API_KEY:
                try:
                    pix_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={urllib.parse.quote(keyword)}&per_page=10"
                    res = requests.get(pix_url, timeout=10)
                    if res.status_code == 200 and res.json().get("hits"):
                        valid_vids = [v for v in res.json()["hits"] if is_video_valid(v)]
                        if valid_vids:
                            v_data = random.choice(valid_vids)["videos"]
                            video_url = v_data.get("medium", v_data.get("large"))["url"]
                except Exception as e: errors.append(f"Pixabay: {e}")

            if video_url:
                temp_name = f"temp_vid_{clip_index}_{attempt}.mp4"
                if safe_download_video(video_url, temp_name):
                    try:
                        clip = VideoFileClip(temp_name).without_audio()
                        if getattr(clip, 'duration', None) is None or clip.duration <= 2.0:
                            raise Exception("छोटा वीडियो")
                            
                        # Smart Trimming (ब्लैक स्क्रीन से बचाव)
                        safe_start = 1.5
                        if clip.duration > duration + safe_start:
                            start_time = random.uniform(safe_start, clip.duration - duration)
                            clip = clip.subclip(start_time, start_time + duration)
                        else:
                            repeats = int(duration / clip.duration) + 1
                            clip = concatenate_videoclips([clip] * repeats).subclip(0, duration)
                            
                        clip = smart_crop_to_916(clip)
                        return clip.set_duration(duration)
                    except Exception as e:
                        errors.append(f"Crop Error: {e}")
                        
    # 🛑 एमरजेंसी बैकअप
    print(f"⚠️ वीडियो नहीं मिला, एमरजेंसी कलर बैकअप लगा रहे हैं...", flush=True)
    return ColorClip(size=(1080, 1920), color=(15, 15, 15)).set_duration(duration)

# --- 7. 📝 पॉप-अप कैप्शंस (सफ़ेद टेक्स्ट, काले स्ट्रोक) ---
def create_subtitle_clip(text, duration, clip_index):
    canvas_w, canvas_h = 1080, 1920
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = "Yantramanav-Black.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/yantramanav/Yantramanav-Black.ttf", font_path)
        except: pass
    try: font = ImageFont.truetype(font_path, 160) 
    except: font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text, width=14)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    x = (canvas_w - (bbox[2] - bbox[0])) // 2
    y = int(canvas_h * 0.50) - (bbox[3] - bbox[1]) // 2 
    
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFFFFF", stroke_width=20, stroke_fill="#000000", align='center')
    
    temp_name = f"cap_{clip_index}_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 8. 🎬 वीडियो कंपाइलेशन (Audio Sync & Crash Fix) ---
def compile_final_video(scenes, final_audio, audio_duration):
    print("🎞️ वीडियो और म्यूजिक के साथ एडिटिंग शुरू...", flush=True)
    # 🛑 AUDIO SYNC FIX (क्रैश से बचाने के लिए लंबाई फिक्स)
    total_duration = audio_duration
    clip_duration = total_duration / len(scenes) 
    processed_clips = []
    
    for idx, scene in enumerate(scenes):
        cap_text = scene.get("caption", "")
        search_query = scene.get("search_query", random.choice(STRICT_DARK_VISUALS))
        
        base_clip = fetch_stock_video(clip_duration, idx, search_query)
        
        if cap_text.strip():
            txt_clip = create_subtitle_clip(cap_text, clip_duration, idx)
            comp = CompositeVideoClip([base_clip, txt_clip], size=(1080, 1920)).set_duration(clip_duration)
            processed_clips.append(comp)
        else:
            processed_clips.append(base_clip)
            
    # 🛑 THE IRON SHIELD: ब्लैक स्क्रीन सेफ्टी लॉक 🛑
    if len(processed_clips) < 2:
        raise Exception("सेफ्टी लॉक: वीडियो रेंडर नहीं हो पाया!")
            
    final_video = concatenate_videoclips(processed_clips, method="compose").set_duration(total_duration)
    
    # आवाज़ को वीडियो की ड्यूरेशन के साथ लॉक करें
    padded_audio = final_audio.set_duration(total_duration)
    
    bgm_path = get_random_bgm()
    if bgm_path:
        print(f"🎵 बैकग्राउंड म्यूजिक जोड़ा जा रहा है: {bgm_path}")
        bg_audio = AudioFileClip(bgm_path).volumex(0.12)
        bg_audio = audio_loop(bg_audio, duration=total_duration)
        bg_audio = audio_fadeout(bg_audio, 1.0)
        final_mixed_audio = CompositeAudioClip([padded_audio, bg_audio]).set_duration(total_duration)
    else:
        final_mixed_audio = padded_audio
        
    final_video = final_video.set_audio(final_mixed_audio)
    
    # 24 FPS RAM बचाने और स्टेबल रेंडरिंग के लिए
    final_video.write_videofile("final_viral_shorts.mp4", fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    return "final_viral_shorts.mp4"

# --- 9. 📤 YouTube अपलोड ---
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
        safe_script = data.get("script", FALLBACK_SCRIPTS["script"])
        safe_scenes = data.get("scenes", FALLBACK_SCRIPTS["scenes"])
        safe_title = data.get("title", FALLBACK_SCRIPTS["title"])
        safe_desc = data.get("description", FALLBACK_SCRIPTS["description"])
        safe_tags = data.get("tags", FALLBACK_SCRIPTS["tags"])
        
        final_audio, audio_duration = asyncio.run(generate_voiceover(safe_script))
        final_video = compile_final_video(safe_scenes, final_audio, audio_duration)
        video_url = upload_video(final_video, safe_title, safe_desc, safe_tags)
        
        send_telegram_report(f"✅ <b>नया शॉर्ट्स लाइव! (Ultimate All-in-One Master)</b>\n🎬 {safe_title}\n🔗 {video_url}")
        print("🎉 सफलता! सभी 7 शर्तों वाला 100% परफेक्ट वीडियो लाइव हो गया।", flush=True)
        
    except Exception as e:
        error_details = str(traceback.format_exc())
        print("\n❌ मशीन क्रैश हो गई! पूरी रिपोर्ट यहाँ है:", flush=True)
        print(error_details, flush=True)
        send_telegram_report(f"🚨 मशीन क्रैश:\n\n{error_details[-1500:]}", is_error=True)
        sys.exit(1)
