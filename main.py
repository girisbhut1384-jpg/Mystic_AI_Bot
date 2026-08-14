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
    AudioFileClip, ImageClip, 
    CompositeVideoClip, CompositeAudioClip, concatenate_videoclips
)
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
TELEGRAM_BOT_TOKEN = clean_key(os.environ.get("TELEGRAM_BOT_TOKEN"))
TELEGRAM_CHAT_ID = clean_key(os.environ.get("TELEGRAM_CHAT_ID"))

# Pexels/Pixabay अब अनिवार्य नहीं हैं, लेकिन अगर हैं तो रहने दें
if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
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
    
    report += "✅ <b>AI Image Engine:</b> Pollinations.ai (100% Free) एक्टिव है।"
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
    except: pass

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
    "Cicada 3301 unsolved internet puzzle",
    "The Max Headroom Incident TV hack",
    "Mt. Gox Crypto Heist billion dollar",
    "KGB Secrets Soviet union spies",
    "Bermuda Triangle of Space satellite anomaly",
    "Dark Web Red Rooms myth or reality",
    "Edward Snowden NSA leaks reality",
    "Stuxnet virus destroying nuclear plants",
    "Anonymous hacker group biggest attacks",
    "Mariana Web and quantum computing",
    "Satoshi Nakamoto Bitcoin creator mystery",
    "Creepy AI and chatbot incidents",
    "Government secret files leaked online",
    "Mysterious websites that suddenly disappeared",
    "Real stories of digital identity theft"
]

FALLBACK_SCRIPTS = {
    "title": "सिल्क रोड का खौफनाक सच! 😱 #shorts",
    "description": "डार्क वेब का असली सच। #DarkWebHindi #SilkRoad #InternetMystery",
    "tags": ["DarkWebHindi", "SilkRoad", "InternetMystery", "shorts"],
    "script": "क्या आपको पता है, डार्क वेब पर एक ऐसा बाज़ार था, जिसका नाम था सिल्क रोड। यहाँ हथियारों से लेकर हैकर्स तक की बोली लगती थी। जब FBI ने यहाँ छापा मारा, तो दुनिया हिल गई। क्योंकि इस काले साम्राज्य का मालिक कोई डॉन नहीं, बल्कि रॉस उलब्रिच्ट नाम का एक आम सा कॉलेज का लड़का था! ऐसे ही डरावने रहस्य जानने के लिए चैनल सब्सक्राइब करें, क्योंकि यही असली वजह है कि...",
    "scenes": [
        {"caption": "क्या आपको पता है?", "image_prompt": "Cinematic dark room with glowing hacker screens"},
        {"caption": "डार्क वेब का बाज़ार", "image_prompt": "Abstract green digital glowing matrix code"},
        {"caption": "नाम था सिल्क रोड", "image_prompt": "Deep underwater dark iceberg mystery"},
        {"caption": "हथियारों की बोली", "image_prompt": "Top secret confidential files in a dark room"},
        {"caption": "FBI का खतरनाक छापा", "image_prompt": "FBI tactical raid flashing police lights night"},
        {"caption": "दुनिया हिल गई", "image_prompt": "NASA control room stressed scientists"},
        {"caption": "मालिक कोई डॉन नहीं", "image_prompt": "Police investigating crime scene at night"},
        {"caption": "आम सा लड़का रॉस था!", "image_prompt": "Normal young college student in hoodie working on laptop"},
        {"caption": "रहस्य जानने के लिए", "image_prompt": "Cyber security glowing digital lock"},
        {"caption": "क्योंकि यही असली वजह है कि...", "image_prompt": "Creepy glowing artificial intelligence eye"}
    ]
}

def get_viral_script():
    print("🧠 AI से नई, परफेक्ट और लूपिंग कहानी लिखी जा रही है...", flush=True)
    used_topics = get_used_topics()
    used_str = ", ".join(used_topics[-5:]) if used_topics else "None"
    
    selected_theme = random.choice(MYSTERY_CATEGORIES)
    
    prompt = f"Write a Hindi YouTube Shorts script about: '{selected_theme}'. Do NOT use these past topics: [{used_str}]. CRITICAL RULE 1: PERFECT LOOP. Must start with 'क्या आपको पता है...' and end EXACTLY with '...सब्सक्राइब करें, क्योंकि यही असली वजह है कि...'. CRITICAL RULE 2: Complete the story (reveal the truth). CRITICAL RULE 3: Use commas for dramatic pauses. CRITICAL RULE 4: Return ONLY valid JSON with keys: 'title', 'description', 'tags', 'script', and 'scenes'. CRITICAL RULE 5: 'scenes' array must have 'caption' (Hindi) and 'image_prompt' (Highly detailed English prompt for AI Image Generator, e.g. 'Cinematic 4K shot of FBI raiding a dark room'). DO NOT invent any other JSON structure."
    
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

# --- 4. 🎧 परफेक्ट डॉक्युमेंट्री आवाज़ ---
async def generate_audio(text):
    print("🎙️ ट्रू क्राइम डॉक्युमेंट्री आवाज़ (विराम के साथ) तैयार हो रही है...", flush=True)
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

# --- 5. 🎨 100% फ्री AI इमेज जनरेटर (Pollinations API) ---
def generate_ai_image(prompt, filename):
    # यह टूल फ्री में 4K लेवल की तस्वीरें बनाता है। nologo=true से वॉटरमार्क नहीं आएगा।
    safe_prompt = urllib.parse.quote(prompt + ", dark cinematic lighting, highly realistic 8k")
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920&nologo=true"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(r.content)
            return True
        return False
    except: return False

# सिनेमैटिक ज़ूम इफ़ेक्ट (Ken Burns Effect)
def apply_ken_burns_effect(image_path, duration):
    # इमेज को हल्का सा ज़ूम करने का इफ़ेक्ट
    clip = ImageClip(image_path).set_duration(duration)
    # Resize function to simulate slow zoom in (Scale up from 1.0 to 1.05)
    return clip.resize(lambda t: 1 + 0.05 * (t / duration)).set_position(('center', 'center'))

def fetch_visual_clip(duration, clip_index, image_prompt):
    print(f"🎨 सीन {clip_index} के लिए AI इमेज जनरेट हो रही है: '{image_prompt}'", flush=True)
    img_name = f"ai_scene_{clip_index}.jpg"
    
    for attempt in range(3):
        if generate_ai_image(image_prompt, img_name):
            try:
                # यहाँ हमने Ken Burns इफ़ेक्ट लगा दिया है ताकि इमेज वीडियो जैसी लगे!
                clip = apply_ken_burns_effect(img_name, duration)
                # स्क्रीन साइज़ पक्का करने के लिए क्रॉप
                clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=1080, height=1920)
                return clip
            except Exception as e:
                print(f"Zoom Effect Error: {e}")
                
    raise Exception(f"AI इमेज जनरेट नहीं हो पाई: {image_prompt}")

# --- 6. 📝 पॉप-अप कैप्शंस (सफ़ेद टेक्स्ट, काले स्ट्रोक के साथ) ---
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

# --- 7. 🎬 वीडियो कंपाइलेशन ---
def compile_final_video(scenes, final_audio, audio_duration):
    print("🎞️ AI इमेजेस और Ken Burns इफ़ेक्ट के साथ 4K एडिटिंग शुरू...", flush=True)
    total_duration = audio_duration + 1.0 
    clip_duration = total_duration / len(scenes) 
    processed_clips = []
    
    for idx, scene in enumerate(scenes):
        cap_text = scene.get("caption", "")
        # अब हम search_query की जगह image_prompt का इस्तेमाल करेंगे
        image_prompt = scene.get("image_prompt", scene.get("search_query", "Dark dramatic true crime scene 4k cinematic"))
        
        base_clip = fetch_visual_clip(clip_duration, idx, image_prompt)
        
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

# --- 8. 📤 YouTube अपलोड ---
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
        
        final_audio, audio_duration = asyncio.run(generate_audio(safe_script))
        final_video = compile_final_video(safe_scenes, final_audio, audio_duration)
        video_url = upload_video(final_video, safe_title, safe_desc, safe_tags)
        
        send_telegram_report(f"✅ <b>नया शॉर्ट्स लाइव! (AI Image + Ken Burns Edition)</b>\n🎬 {safe_title}\n🔗 {video_url}")
        print("🎉 सफलता! 100% सटीक AI विजुअल वाला वीडियो लाइव हो गया।", flush=True)
        
    except Exception as e:
        error_details = str(traceback.format_exc())
        send_telegram_report(f"🚨 मशीन क्रैश:\n\n{error_details[-1500:]}", is_error=True)
        sys.exit(1)
