import os
import sys
import requests
import time
import random
import textwrap
import json
import urllib.parse
import traceback
import asyncio
from datetime import datetime, timedelta, timezone
from moviepy.editor import AudioFileClip, concatenate_videoclips, CompositeVideoClip, VideoFileClip, ImageClip, CompositeAudioClip
from PIL import Image, ImageDraw, ImageFont
import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 1. API क्रेडेंशियल्स ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, PEXELS_API_KEY, PIXABAY_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ एरर: GitHub Secrets में API Keys गायब हैं!")
    sys.exit(1)

# यूट्यूब API सेटअप
creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
youtube = build("youtube", "v3", credentials=creds)

# --- 2. टेलीग्राम रिपोर्टिंग ---
def send_telegram_report(message):
    try: 
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})
    except: 
        pass

# --- 3. एडवांस API हेल्थ चेकर ---
def check_api_health():
    print("🔍 API Keys की जाँच की जा रही है...")
    report = "🛠️ <b>API हेल्थ रिपोर्ट:</b>\n\n"
    
    try:
        pex_res = requests.get("https://api.pexels.com/videos/search?query=nature&per_page=1", headers={"Authorization": PEXELS_API_KEY}, timeout=10)
        if pex_res.status_code == 200: report += "✅ <b>Pexels:</b> बिल्कुल सही काम कर रहा है।\n"
        else: report += f"🔴 <b>Pexels:</b> काम नहीं कर रहा (Error {pex_res.status_code})।\n"
    except Exception as e: report += f"❌ <b>Pexels:</b> कनेक्ट नहीं हो पा रहा।\n"

    try:
        pix_res = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q=nature&per_page=3", timeout=10)
        if pix_res.status_code == 200: report += "✅ <b>Pixabay:</b> बिल्कुल सही काम कर रहा है।\n"
        else: report += f"🔴 <b>Pixabay:</b> काम नहीं कर रहा (Error {pix_res.status_code})।\n"
    except Exception as e: report += f"❌ <b>Pixabay:</b> कनेक्ट नहीं हो पा रहा।\n"

    send_telegram_report(report)

# --- 4. ऑटो-डिलीट सिस्टम (100 व्यू से कम वाले) ---
def clean_low_performing_videos():
    print("🧹 पुराने फ्लॉप वीडियो को स्कैन करके डिलीट किया जा रहा है...")
    try:
        deleted_count = 0
        request = youtube.channels().list(part="contentDetails", mine=True)
        response = request.execute()
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        playlist_request = youtube.playlistItems().list(part="snippet", playlistId=uploads_playlist_id, maxResults=50)
        playlist_response = playlist_request.execute()
        
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        
        for item in playlist_response.get('items', []):
            video_id = item['snippet']['resourceId']['videoId']
            published_at_str = item['snippet']['publishedAt'].replace('Z', '+00:00')
            published_at = datetime.fromisoformat(published_at_str)
            
            if published_at < seven_days_ago:
                stats_req = youtube.videos().list(part="statistics", id=video_id)
                stats_res = stats_req.execute()
                
                if stats_res.get('items'):
                    views = int(stats_res['items'][0]['statistics'].get('viewCount', 0))
                    if views < 100:
                        youtube.videos().delete(id=video_id).execute()
                        deleted_count += 1
                        time.sleep(1)
                        
        if deleted_count > 0:
            send_telegram_report(f"🧹 <b>चैनल क्लीनअप:</b> {deleted_count} फ्लॉप वीडियो डिलीट किए गए।")
            print(f"✅ {deleted_count} फ्लॉप वीडियो हटाए गए।")
    except Exception as e:
        print(f"⚠️ क्लीनअप में एरर: {e}")

# --- 5. 30+ डायनामिक कीवर्ड्स ---
TECH_KEYWORDS = [
    "hacker typing", "neon server", "cyber security", "matrix code", "dark web", 
    "data center", "abstract tech", "glitch", "ai brain", "future technology",
    "circuit board", "smartphone close up", "code scrolling", "server room"
]

# --- 6. 100% क्रैश-फ्री स्क्रिप्ट जनरेशन (Pollinations AI) ---
def get_viral_script():
    print("🧠 AI से नई कहानी लिखी जा रही है...")
    topics = ["साइबर सिक्योरिटी", "आर्टिफिशियल इंटेलिजेंस", "डीप वेब", "अंतरिक्ष रहस्य"]
    prompt = f"""Write a mystery tech script about '{random.choice(topics)}' for a 45-second YouTube Short. Hindi language. 
    IMPORTANT: The script MUST end with a strong Call to Action (CTA).
    Return ONLY a JSON with keys: 'title', 'description', 'tags', 'script', 'captions' (array of 5 short Hindi phrases)."""
    
    try:
        url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
        response = requests.get(url, timeout=30)
        content = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        return {
            "title": "इंटरनेट का काला सच! 😱 #shorts",
            "description": "इंटरनेट के रहस्य! #mystery",
            "tags": ["mystery", "hacker", "shorts"],
            "script": "इंटरनेट की दुनिया जितनी साफ़ दिखती है, अंदर से उतनी ही खौफनाक है। हर सेकंड कोई बड़ा सर्वर हैक हो रहा है। ऐसे ही रहस्य जानने के लिए अभी सब्सक्राइब करें!",
            "captions": ["इंटरनेट का काला सच", "सर्वर हैक", "डेटा चोरी", "भयानक रहस्य", "अभी सब्सक्राइब करें"]
        }

# --- 7. आवाज़ और बैकग्राउंड म्यूजिक (BGM) ---
async def generate_audio(text):
    print("🎙️ आवाज़ तैयार हो रही है...")
    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
    await communicate.save("voice.mp3")
    
    main_audio = AudioFileClip("voice.mp3")
    
    # BGM लॉजिक (अगर bgm.mp3 फाइल मौजूद है तो)
    if os.path.exists("bgm.mp3"):
        print("🎵 बैकग्राउंड म्यूजिक जोड़ा जा रहा है...")
        bg_audio = AudioFileClip("bgm.mp3").volumex(0.15)
        from moviepy.audio.fx.all import audio_loop
        bg_audio = audio_loop(bg_audio, duration=main_audio.duration)
        return CompositeAudioClip([main_audio, bg_audio]), main_audio.duration
        
    return main_audio, main_audio.duration

# --- 8. स्मार्ट स्टॉक वीडियो (Pexels + Pixabay Fallback) ---
def fetch_stock_video(duration):
    keyword = random.choice(TECH_KEYWORDS)
    video_url = None

    try:
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&per_page=15&page={random.randint(1, 3)}&orientation=portrait"
        res = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=10)
        if res.status_code == 200 and res.json().get("videos"):
            video_url = sorted(random.choice(res.json()["videos"])["video_files"], key=lambda x: x['width'] * x['height'], reverse=True)[0]["link"]
    except: pass

    if not video_url:
        try:
            pix_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={urllib.parse.quote(keyword)}&per_page=10"
            res = requests.get(pix_url, timeout=10)
            if res.status_code == 200 and res.json().get("hits"):
                video_url = random.choice(res.json()["hits"])["videos"].get("large", random.choice(res.json()["hits"])["videos"].get("medium"))["url"]
        except: pass

    if video_url:
        try:
            temp_name = f"temp_{random.randint(1,9999)}.mp4"
            urllib.request.urlretrieve(video_url, temp_name)
            clip = VideoFileClip(temp_name).without_audio()
            
            if clip.duration > duration + 1:
                start_time = random.uniform(0, clip.duration - duration - 1)
                clip = clip.subclip(start_time, start_time + duration)
            else:
                clip = concatenate_videoclips([clip] * (int(duration / clip.duration) + 1)).subclip(0, duration)
                
            return clip.resize(height=1920).crop(x_center=clip.w/2, y_center=1920/2, width=1080, height=1920)
        except: pass

    # सेफ बैकग्राउंड (Black Screen नहीं)
    img = Image.new('RGB', (1080, 1920), color=(15, 25, 45))
    img.save("safe_fallback.jpg")
    return ImageClip("safe_fallback.jpg").set_duration(duration)

# --- 9. सेंटर सबटाइटल्स (Black Stroke) ---
def create_subtitle_clip(text, duration):
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
    
    temp_name = f"cap_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 10. वीडियो कंपाइलेशन (Smooth Ending) ---
def compile_final_video(captions, final_audio, audio_duration):
    total_duration = audio_duration + 2.0 
    clip_duration = total_duration / len(captions)
    processed_clips = []
    
    for cap_text in captions:
        base_clip = fetch_stock_video(clip_duration)
        if cap_text.strip():
            processed_clips.append(CompositeVideoClip([base_clip, create_subtitle_clip(cap_text, clip_duration)], size=(1080, 1920)))
        else:
            processed_clips.append(base_clip)
            
    final_video = concatenate_videoclips(processed_clips, method="compose").set_audio(final_audio).set_duration(total_duration)
    final_video.write_videofile("final_viral_shorts.mp4", fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    return "final_viral_shorts.mp4"

# --- 11. YouTube अपलोड ---
def upload_video(video_file, title, description, tags):
    request_body = {"snippet": {"categoryId": "22", "title": title, "description": description, "tags": tags}, "status": {"privacyStatus": "public", "madeForKids": False}}
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    res = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    return f"https://youtu.be/{res['id']}"

if __name__ == "__main__":
    try:
        check_api_health()
        clean_low_performing_videos()
        
        data = get_viral_script()
        final_audio, audio_duration = asyncio.run(generate_audio(data["script"]))
        final_video = compile_final_video(data["captions"], final_audio, audio_duration)
        video_url = upload_video(final_video, data["title"], data["description"], data["tags"])
        
        send_telegram_report(f"✅ <b>नया शॉर्ट्स लाइव!</b>\n🎬 {data['title']}\n🔗 {video_url}")
    except Exception as e:
        send_telegram_report(f"🚨 <b>मशीन क्रैश:</b>\n{str(traceback.format_exc())[:300]}")
        sys.exit(1)
