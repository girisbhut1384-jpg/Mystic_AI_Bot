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
    except: pass

# --- 3. 🚀 कंटेक्स्ट-टू-वीडियो डोमेन इंजन (Context-to-Video Engine) ---
# अब मशीन जिस विषय की कहानी चुनेगी, सिर्फ उसी विषय के सटीक विजुअल्स का इस्तेमाल करेगी
DOMAINS = {
    "SPACE": {
        "topics": ["Bermuda Triangle of Space satellite anomaly", "Black Knight Satellite mystery", "NASA secret space transmissions"],
        "visuals": ["cinematic 4k satellite deep space", "NASA control room scientists looking stressed", "glowing galaxy black hole mystery", "meteorite falling space night", "international space station orbit dark"]
    },
    "CYBER": {
        "topics": ["Silk Road Ross Ulbricht FBI raid", "Mt. Gox Crypto Heist billion dollar", "Anonymous hacker group biggest attacks", "Stuxnet virus destroying nuclear plants"],
        "visuals": ["glowing digital black market interface", "FBI agents tactical gear breaking door", "normal college student hoodie laptop quiet room", "abstract green digital code hacking", "cyber security digital lock"]
    },
    "GOVERNMENT": {
        "topics": ["KGB Secrets Soviet union spies", "Edward Snowden NSA leaks reality", "Government secret files leaked online"],
        "visuals": ["classified top secret folder", "soviet kgb spy files", "police investigating crime scene night", "abandoned dark government building", "detective board strings mystery"]
    },
    "MYSTERY": {
        "topics": ["Cicada 3301 unsolved internet puzzle", "Dark Web Red Rooms myth or reality", "Creepy AI and chatbot incidents", "Mysterious websites that suddenly disappeared"],
        "visuals": ["creepy artificial intelligence eye glowing", "dark deep web mystery iceberg", "dark abandoned server farm", "creepy static tv screen noise", "hacker typing dark room"]
    }
}

FALLBACK_SCRIPTS = [
    {
        "title": "सिल्क रोड का खौफनाक सच! 😱 #shorts",
        "description": "डार्क वेब का असली सच। #DarkWebHindi #SilkRoad #InternetMystery",
        "tags": ["DarkWebHindi", "SilkRoad", "InternetMystery", "shorts"],
        "script": "क्या आपको पता है, डार्क वेब पर एक ऐसा बाज़ार था, जिसका नाम था सिल्क रोड। यहाँ हथियारों से लेकर हैकर्स तक की बोली लगती थी। जब FBI ने यहाँ छापा मारा, तो दुनिया हिल गई। क्योंकि इस काले साम्राज्य का मालिक कोई डॉन नहीं, बल्कि रॉस उलब्रिच्ट नाम का एक आम सा कॉलेज का लड़का था! ऐसे ही डरावने रहस्य जानने के लिए चैनल सब्सक्राइब करें, क्योंकि यही असली वजह है कि...",
        "scenes": [
            {"caption": "क्या आपको पता है?", "search_query": "hacker typing dark room"},
            {"caption": "डार्क वेब का बाज़ार", "search_query": "glowing digital black market interface"},
            {"caption": "नाम था सिल्क रोड", "search_query": "abstract green digital code hacking"},
            {"caption": "हथियारों की बोली", "search_query": "classified top secret folder"},
            {"caption": "FBI का खतरनाक छापा", "search_query": "FBI agents tactical gear breaking door"},
            {"caption": "दुनिया हिल गई", "search_query": "NASA control room scientists looking stressed"},
            {"caption": "मालिक कोई डॉन नहीं", "search_query": "police investigating crime scene night"},
            {"caption": "आम सा लड़का रॉस था!", "search_query": "normal college student hoodie laptop quiet room"},
            {"caption": "रहस्य जानने के लिए", "search_query": "cyber security digital lock"},
            {"caption": "क्योंकि यही असली वजह है कि...", "search_query": "dark deep web mystery iceberg"}
        ]
    }
]

# AI को जिस डोमेन की कहानी मिलेगी, विजुअल्स सिर्फ उसी डोमेन के होंगे
def get_viral_script():
    print("🧠 AI से कंटेक्स्ट-आधारित नई लूपिंग कहानी लिखी जा रही है...", flush=True)
    domain_name = random.choice(list(DOMAINS.keys()))
    selected_theme = random.choice(DOMAINS[domain_name]["topics"])
    allowed_visuals = DOMAINS[domain_name]["visuals"]
    allowed_list_str = ", ".join([f"'{k}'" for k in allowed_visuals])
    
    prompt = f"Write a Hindi YouTube Shorts script about: '{selected_theme}'. CRITICAL RULE 1: PERFECT LOOP. Must start with 'क्या आपको पता है...' and end EXACTLY with '...सब्सक्राइब करें, क्योंकि यही असली वजह है कि...'. CRITICAL RULE 2: Complete the story (reveal the truth/culprit). CRITICAL RULE 3: Use commas and periods for dramatic pauses. CRITICAL RULE 4: Return ONLY valid JSON with keys: 'title', 'description', 'tags', 'script', and 'scenes'. CRITICAL RULE 5: 'scenes' array 'search_query' MUST be EXACTLY from this list: [{allowed_list_str}]."
    
    for _ in range(3):
        try:
            url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
            res = requests.get(url, timeout=25)
            content = res.text.replace("```json", "").replace("```", "").strip()
            if "{" in content and "}" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            data = json.loads(content)
            
            # विजुअल वैलिडेशन: अगर कीवर्ड डोमेन लिस्ट में नहीं है तो बदल दो
            if "scenes" in data:
                for scene in data["scenes"]:
                    if scene.get("search_query") not in allowed_visuals:
                        scene["search_query"] = random.choice(allowed_visuals)
                        
            if isinstance(data, dict) and "script" in data and "scenes" in data:
                return data, allowed_visuals
        except: time.sleep(2)
    return random.choice(FALLBACK_SCRIPTS), DOMAINS["CYBER"]["visuals"]

# --- 4. 🎧 खौफनाक ट्रू क्राइम आवाज़ (Pitch -15Hz, Rate -20%) ---
async def generate_audio(text):
    print("🎙️ डॉक्युमेंट्री/हॉरर सस्पेंस आवाज़ तैयार हो रही है...", flush=True)
    for _ in range(3):
        try:
            # सस्पेंस को बहुत गहरा करने के लिए पैरामीटर्स एक्सट्रीम सेट किये गए हैं
            communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="-20%", pitch="-15Hz")
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

# --- 5. 🛡️ द अल्टीमेट नेगेटिव कीवर्ड फिल्टर (Anti-Garbage v2) ---
# अब ऑफिस वर्कर, गेमर, 3D चश्मे, और फुटबॉल कभी नहीं आएंगे
BLACKLIST_WORDS = [
    "toy", "jellyfish", "football", "soccer", "dance", "dancing", "party", 
    "girl", "kid", "child", "baby", "game", "playing", "abstract", "texture", 
    "happy", "smiling", "sunny", "office", "worker", "corridor", "3d glasses",
    "mask", "guy fawkes", "cartoon", "animation", "women working", "laughing"
]

def is_video_valid(video_data):
    video_text = str(video_data).lower()
    for word in BLACKLIST_WORDS:
        if word in video_text:
            return False
    return True

# --- 6. 🎥 सटीक 4K सिनेमैटिक विजुअल्स (डोमेन के हिसाब से) ---
def fetch_stock_video(duration, clip_index, search_query, allowed_visuals):
    errors = []
    print(f"🔍 सीन {clip_index} के लिए ढूँढ रहे हैं (नेगेटिव फिल्टर ऑन): '{search_query}'", flush=True)
    
    fallback_query = search_query.split(" ")[0] + " " + search_query.split(" ")[1] if len(search_query.split(" ")) > 1 else search_query
    keywords_to_try = [search_query, fallback_query, random.choice(allowed_visuals)]
    
    for keyword in keywords_to_try:
        for attempt in range(3):
            video_url = None
            try:
                page = random.randint(1, 2)
                url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&per_page=15&page={page}&orientation=portrait"
                res = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=10)
                if res.status_code == 200 and res.json().get("videos"):
                    sorted_videos = sorted(res.json()["videos"], key=lambda x: x['width'] * x['height'], reverse=True)
                    for vid in sorted_videos:
                        if is_video_valid(vid):
                            video_url = vid["video_files"][0]["link"]
                            break
            except Exception as e: errors.append(f"Pexels: {e}")

            if not video_url and PIXABAY_API_KEY:
                try:
                    pix_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={urllib.parse.quote(keyword)}&per_page=10"
                    res = requests.get(pix_url, timeout=10)
                    if res.status_code == 200 and res.json().get("hits"):
                        for vid in res.json()["hits"]:
                            if is_video_valid(vid):
                                video_url = vid["videos"].get("large", vid["videos"].get("medium"))["url"]
                                break
                except Exception as e: errors.append(f"Pixabay: {e}")

            if video_url:
                temp_name = f"temp_vid_{clip_index}_{attempt}.mp4"
                if safe_download_video(video_url, temp_name):
                    try:
                        clip = VideoFileClip(temp_name).without_audio()
                        if getattr(clip, 'duration', None) is None or clip.duration <= 2.0:
                            raise Exception("वीडियो बहुत छोटा है")
                            
                        # Smart Trimming
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
    raise Exception("सटीक वीडियो नहीं मिल पाया (ब्लैकलिस्ट की वजह से रिजेक्ट)।")

# --- 7. डायनामिक कैप्शंस (सफ़ेद टेक्स्ट, लाल/काला बैकग्राउंड) ---
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
    
    # सफ़ेद टेक्स्ट और गाढ़ा काला स्ट्रोक (पढ़ने में आसान)
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFFFFF", stroke_width=20, stroke_fill="#000000", align='center')
    
    temp_name = f"cap_{clip_index}_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 8. वीडियो कंपाइलेशन ---
def compile_final_video(scenes, final_audio, audio_duration, allowed_visuals):
    print("🎞️ कंटेक्स्ट-अवेयर 4K एडिटिंग शुरू हो रही है...", flush=True)
    total_duration = audio_duration + 1.0 
    clip_duration = total_duration / len(scenes) 
    processed_clips = []
    
    for idx, scene in enumerate(scenes):
        cap_text = scene.get("caption", "")
        search_query = scene.get("search_query", random.choice(allowed_visuals))
        if search_query not in allowed_visuals:
            search_query = random.choice(allowed_visuals)
            
        base_clip = fetch_stock_video(clip_duration, idx, search_query, allowed_visuals)
        
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
        
        data, allowed_visuals = get_viral_script()
        safe_script = data.get("script", FALLBACK_SCRIPTS[0]["script"])
        safe_scenes = data.get("scenes", FALLBACK_SCRIPTS[0]["scenes"])
        safe_title = data.get("title", FALLBACK_SCRIPTS[0]["title"])
        safe_desc = data.get("description", FALLBACK_SCRIPTS[0]["description"])
        safe_tags = data.get("tags", FALLBACK_SCRIPTS[0]["tags"])
        
        final_audio, audio_duration = asyncio.run(generate_audio(safe_script))
        final_video = compile_final_video(safe_scenes, final_audio, audio_duration, allowed_visuals)
        video_url = upload_video(final_video, safe_title, safe_desc, safe_tags)
        
        send_telegram_report(f"✅ <b>नया शॉर्ट्स लाइव! (Context-to-Video Engine Active)</b>\n🎬 {safe_title}\n🔗 {video_url}")
        print("🎉 सफलता! 100% परफेक्ट वीडियो लाइव हो गया।", flush=True)
        
    except Exception as e:
        error_details = str(traceback.format_exc())
        send_telegram_report(f"🚨 मशीन क्रैश:\n\n{error_details[-1500:]}", is_error=True)
        sys.exit(1)
