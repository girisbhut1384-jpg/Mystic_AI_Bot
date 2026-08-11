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
    if not is_error: payload["parse_mode"] = "HTML"
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

# --- 5. 🚀 द अल्टीमेट वायरल विजुअल डिक्शनरी ---
# AI अब खुद से कोई भी फालतू कीवर्ड (जैसे Silk Road या Toy Car) नहीं बना पाएगा।
# उसे हर सीन के लिए इन्ही में से एक चुनना होगा, जो Pexels पर 100% सही और डार्क वीडियो ही देते हैं।
GUARANTEED_DARK_VISUALS = [
    "hacker typing dark room", 
    "police siren flashing lights night",
    "abstract green digital code", 
    "secret confidential files document",
    "dark abandoned building night", 
    "hooded man computer dark",
    "cyber security digital lock", 
    "server room blinking lights",
    "arrest handcuffs police", 
    "iceberg underwater dark",
    "detective investigation board"
]

FALLBACK_SCRIPTS = [
    {
        "title": "सिल्क रोड का खौफनाक सच! 😱 #shorts",
        "description": "डार्क वेब का असली सच और सिल्क रोड की कहानी। #DarkWebHindi #SilkRoad #InternetMystery",
        "tags": ["DarkWebHindi", "SilkRoad", "InternetMystery", "shorts"],
        "script": "क्या आपको पता है, आप इंटरनेट पर जो भी करते हैं, वो कोई और भी देख सकता है? डार्क वेब पर एक ऐसा बाज़ार था, जिसका नाम था सिल्क रोड। यहाँ हैकर्स से लेकर हथियारों तक की बोली लगती थी। जब FBI ने यहाँ छापा मारा, तो दुनिया हिल गई। क्योंकि इस काले साम्राज्य का मालिक कोई डॉन नहीं, बल्कि रॉस उलब्रिच्ट नाम का एक आम सा कॉलेज का लड़का था! ऐसे ही डरावने रहस्य जानने के लिए अभी सब्सक्राइब करें!",
        "scenes": [
            {"caption": "क्या आपको पता है?", "search_query": "hacker typing dark room"},
            {"caption": "कोई आपको देख रहा है", "search_query": "cyber security digital lock"},
            {"caption": "डार्क वेब का बाज़ार", "search_query": "abstract green digital code"},
            {"caption": "नाम था सिल्क रोड", "search_query": "secret confidential files document"},
            {"caption": "हथियारों की बोली", "search_query": "dark abandoned building night"},
            {"caption": "FBI का खतरनाक छापा", "search_query": "police siren flashing lights night"},
            {"caption": "दुनिया हिल गई", "search_query": "server room blinking lights"},
            {"caption": "मालिक कोई डॉन नहीं", "search_query": "hooded man computer dark"},
            {"caption": "आम सा लड़का रॉस था!", "search_query": "arrest handcuffs police"},
            {"caption": "अभी सब्सक्राइब करें", "search_query": "abstract green digital code"}
        ]
    }
]

MYSTERY_TOPICS = [
    "Silk Road Ross Ulbricht FBI raid dark web", 
    "Cicada 3301 mystery internet puzzle", 
    "Deep Web Iceberg 96 percent reality", 
    "Edward Snowden NSA leaks secret files", 
    "Stuxnet computer virus destruction"
]

def get_viral_script():
    print("🧠 AI से सटीक विजुअल्स वाली कहानी लिखी जा रही है...", flush=True)
    selected_theme = random.choice(MYSTERY_TOPICS)
    
    # प्रॉम्प्ट में AI की नकेल कसी गई है: "सिर्फ GUARANTEED_DARK_VISUALS में से ही कीवर्ड चुनो"
    allowed_list_str = ", ".join([f"'{k}'" for k in GUARANTEED_DARK_VISUALS])
    
    prompt = f"Write a Hindi YouTube Shorts script about: '{selected_theme}'. Rule 1: Shocking hook in first 3 seconds. Rule 2: NEVER leave a mystery incomplete. Name the real culprit/fact. Rule 3: Return ONLY valid JSON with keys: 'title', 'description', 'tags', 'script', and 'scenes'. Rule 4: 'scenes' is an array of objects. Each object has 'caption' (Hindi) and 'search_query'. CRITICAL: 'search_query' MUST be picked EXACTLY from this list and nowhere else: [{allowed_list_str}]. Do not invent queries."
    
    for _ in range(3):
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
            res = requests.get(url, timeout=25)
            content = res.text.replace("```json", "").replace("```", "").strip()
            if "{" in content and "}" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            data = json.loads(content)
            
            # विजुअल वैलिडेशन: अगर AI ने लिस्ट से बाहर का कीवर्ड दिया, तो हम उसे बदल देंगे
            if "scenes" in data:
                for scene in data["scenes"]:
                    if scene.get("search_query") not in GUARANTEED_DARK_VISUALS:
                        scene["search_query"] = random.choice(GUARANTEED_DARK_VISUALS)
                        
            if isinstance(data, dict) and "script" in data and "scenes" in data:
                return data
        except: time.sleep(2)
    
    return random.choice(FALLBACK_SCRIPTS)

# --- 6. 🎧 सस्पेंस डॉक्यूमेंट्री वाली आवाज़ (Rate -20%, Pitch -10Hz) ---
async def generate_audio(text):
    print("🎙️ थ्रिलर डॉक्युमेंट्री जैसी आवाज़ तैयार हो रही है...", flush=True)
    for _ in range(3):
        try:
            # आवाज़ को और भारी और धीमा किया गया है ताकि इंसानी इमोशन (सस्पेंस) फील हो
            communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="-20%", pitch="-10Hz")
            await communicate.save("voice.mp3")
            main_audio = AudioFileClip("voice.mp3")
            if os.path.exists("bgm.mp3"):
                try:
                    # BGM वॉल्यूम
                    bg_audio = AudioFileClip("bgm.mp3").volumex(0.15)
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

# --- 8. 🎥 सटीक 4K विजुअल्स ---
def fetch_stock_video(duration, clip_index, search_query):
    errors = []
    print(f"🔍 सीन {clip_index} के लिए ढूँढ रहे हैं: '{search_query}'", flush=True)
    
    # अगर Pexels न चले, तो Pixabay के लिए छोटा कीवर्ड
    fallback_query = search_query.split(" ")[0] + " " + search_query.split(" ")[1] if len(search_query.split(" ")) > 1 else search_query
    keywords_to_try = [search_query, fallback_query, random.choice(GUARANTEED_DARK_VISUALS)]
    
    for keyword in keywords_to_try:
        for attempt in range(2):
            video_url = None
            try:
                page = random.randint(1, 2)
                url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&per_page=15&page={page}&orientation=portrait"
                res = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=10)
                if res.status_code == 200 and res.json().get("videos"):
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

# --- 9. पॉप-अप कैप्शंस (हाईलाइट के साथ) ---
def create_subtitle_clip(text, duration, clip_index):
    canvas_w, canvas_h = 1080, 1920
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = "Yantramanav-Black.ttf"
    if not os.path.exists(font_path):
        try: urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/yantramanav/Yantramanav-Black.ttf", font_path)
        except: pass
    try: font = ImageFont.truetype(font_path, 160) # फॉन्ट और भी बड़ा और बोल्ड किया है
    except: font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text, width=12)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    x = (canvas_w - (bbox[2] - bbox[0])) // 2
    
    # कैप्शंस को स्क्रीन के बिल्कुल बीच (Center) में रखा है
    y = int(canvas_h * 0.50) - (bbox[3] - bbox[1]) // 2 
    
    # चमकदार पीला (Neon Yellow) और गाढ़ा काला स्ट्रोक (Black Outline)
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFFF00", stroke_width=20, stroke_fill="#000000", align='center')
    
    temp_name = f"cap_{clip_index}_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 10. वीडियो कंपाइलेशन ---
def compile_final_video(scenes, final_audio, audio_duration):
    print("🎞️ विजुअल सिंक के साथ एडिटिंग शुरू हो रही है...", flush=True)
    total_duration = audio_duration + 2.0 
    clip_duration = total_duration / len(scenes) 
    processed_clips = []
    
    for idx, scene in enumerate(scenes):
        cap_text = scene.get("caption", "")
        # अगर AI कोई फालतू कीवर्ड दे दे, तो भी हमारी डिक्शनरी उसे बचा लेगी
        search_query = scene.get("search_query", random.choice(GUARANTEED_DARK_VISUALS))
        if search_query not in GUARANTEED_DARK_VISUALS:
            search_query = random.choice(GUARANTEED_DARK_VISUALS)
            
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
        
        send_telegram_report(f"✅ <b>नया शॉर्ट्स लाइव! (No Toy Cars, Perfect Sync)</b>\n🎬 {safe_title}\n🔗 {video_url}")
        print("🎉 सफलता! 100% सटीक विजुअल वाला वीडियो लाइव हो गया।", flush=True)
        
    except Exception as e:
        error_details = str(traceback.format_exc())
        send_telegram_report(f"🚨 मशीन क्रैश:\n\n{error_details[-1500:]}", is_error=True)
        sys.exit(1)
