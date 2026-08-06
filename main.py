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
import nest_asyncio
from datetime import datetime, timedelta, timezone
from moviepy.editor import AudioFileClip, concatenate_videoclips, CompositeVideoClip, VideoFileClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
import edge_tts
import g4f
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

nest_asyncio.apply()

# --- 1. सभी API क्रेडेंशियल्स ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, PEXELS_API_KEY, PIXABAY_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ एरर: GitHub Secrets में कोई API Key या Telegram टोकन गायब है!")
    sys.exit(1)

# यूट्यूब API सेटअप
creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
youtube = build("youtube", "v3", credentials=creds)

# --- 2. टेलीग्राम रिपोर्टिंग सिस्टम ---
def send_telegram_report(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: 
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})
    except: 
        pass

# --- 3. ऑटो-डिलीट सिस्टम (100 व्यू से कम वाले) ---
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
            
            # सिर्फ 7 दिन से पुराने वीडियो चेक करेगा
            if published_at < seven_days_ago:
                stats_req = youtube.videos().list(part="statistics", id=video_id)
                stats_res = stats_req.execute()
                
                if stats_res.get('items'):
                    views = int(stats_res['items'][0]['statistics'].get('viewCount', 0))
                    # अगर 100 से कम व्यूज हैं, तो उड़ा देगा
                    if views < 100:
                        youtube.videos().delete(id=video_id).execute()
                        deleted_count += 1
                        time.sleep(1)
                        
        if deleted_count > 0:
            send_telegram_report(f"🧹 <b>चैनल क्लीनअप:</b> {deleted_count} फ्लॉप वीडियो डिलीट किए गए।")
            print(f"✅ {deleted_count} फ्लॉप वीडियो हटाए गए।")
    except Exception as e:
        print(f"⚠️ क्लीनअप में एरर: {e}")

# --- 4. स्क्रिप्ट और कीवर्ड जनरेशन ---
def get_viral_script():
    print("🧠 फ्री AI से नई कहानी और सर्च कीवर्ड्स लिखे जा रहे हैं...")
    topics = ["साइबर सिक्योरिटी", "आर्टिफिशियल इंटेलिजेंस का भविष्य", "डीप वेब के रहस्य", "अंतरिक्ष के अनसुलझे रहस्य", "भविष्य की तकनीक"]
    selected_topic = random.choice(topics)
    
    prompt = f"Write a mystery tech script about '{selected_topic}' for a 45-second YouTube Short. Hindi language. Return ONLY a JSON with keys: 'title', 'description', 'tags', 'script' (Hindi narration only), 'captions' (array of 5 short Hindi phrases), 'keywords' (array of 5 English ONE OR TWO WORD search terms for stock video websites, like 'hacker', 'matrix', 'space', 'technology')."
    
    try:
        response = g4f.ChatCompletion.create(model=g4f.models.gpt_35_turbo, messages=[{"role": "user", "content": prompt}])
        content = response.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        return {
            "title": "दुनिया का सबसे बड़ा हैकर! 😱 #shorts",
            "description": "इंटरनेट का काला सच! #mystery #hacker #tech #hindi",
            "tags": ["mystery", "hacker", "tech", "shorts", "hindi"],
            "script": "इंटरनेट की दुनिया जितनी बाहर से साफ़ दिखती है, अंदर से उतनी ही खौफनाक है। क्या आप जानते हैं कि हर सेकंड में दुनिया का कोई न कोई बड़ा सर्वर हैक हो रहा है? आपकी जानकारी भी खतरे में हो सकती है।",
            "captions": ["इंटरनेट का काला सच", "खौफनाक दुनिया", "बड़े सर्वर हैक", "आपकी जानकारी खतरे में", "तुरंत सावधान हो जाएं"],
            "keywords": ["hacker", "dark web", "server room", "cyber security", "data matrix"]
        }

# --- 5. फ्री असली आवाज़ ---
async def generate_audio(text):
    print("🎙️ आवाज़ (Madhur) तैयार हो रही है...")
    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
    await communicate.save("voice.mp3")
    return "voice.mp3"

# --- 6. स्मार्ट स्टॉक वीडियो डाउनलोडर (Pexels + Pixabay) ---
def fetch_stock_video(keyword, duration, index):
    print(f"📥 कीवर्ड '{keyword}' के लिए स्टॉक वीडियो ढूंढा जा रहा है...")
    vid_name = f"stock_{index}.mp4"
    video_url = None

    try:
        page = random.randint(1, 3) 
        pexel_api = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&per_page=15&page={page}&orientation=portrait"
        res = requests.get(pexel_api, headers={"Authorization": PEXELS_API_KEY}, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get("videos"):
                video = random.choice(data["videos"])
                video_files = sorted(video["video_files"], key=lambda x: x['width'] * x['height'], reverse=True)
                video_url = video_files[0]["link"]
    except: pass

    if not video_url:
        try:
            pixabay_api = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={urllib.parse.quote(keyword)}&per_page=10"
            res = requests.get(pixabay_api, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if data.get("hits"):
                    video = random.choice(data["hits"])
                    video_url = video["videos"]["large"]["url"]
        except: pass

    if video_url:
        try:
            urllib.request.urlretrieve(video_url, vid_name)
            clip = VideoFileClip(vid_name).without_audio()
            if clip.duration > duration + 1:
                start_time = random.uniform(0, clip.duration - duration - 1)
                clip = clip.subclip(start_time, start_time + duration)
            else:
                repeats = int(duration / clip.duration) + 1
                clip = concatenate_videoclips([clip] * repeats).subclip(0, duration)
            clip = clip.resize(height=1920)
            x_center = clip.w / 2
            clip = clip.crop(x_center=x_center, y_center=1920/2, width=1080, height=1920)
            return clip
        except Exception as e:
            pass

    img = Image.new('RGB', (1080, 1920), color=(20, 20, 25))
    img.save(f"fallback_{index}.jpg")
    return ImageClip(f"fallback_{index}.jpg").set_duration(duration)

# --- 7. विशाल देवनागरी कैप्शन्स ---
def create_hindi_caption(text, duration):
    canvas_w, canvas_h = 1080, 500
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_path = "Yantramanav-Black.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://raw.githubusercontent.com/google/fonts/main/ofl/yantramanav/Yantramanav-Black.ttf"
            urllib.request.urlretrieve(url, font_path)
        except: pass
    
    try: font = ImageFont.truetype(font_path, 130) 
    except: font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text, width=14)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    x = (canvas_w - (bbox[2] - bbox[0])) // 2
    y = (canvas_h - (bbox[3] - bbox[1])) // 2
    
    draw.multiline_text((x+8, y+8), wrapped, font=font, fill="black", align='center')
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFE81F", stroke_width=18, stroke_fill="black", align='center')
    
    temp_name = f"cap_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 8. वीडियो को जोड़ना ---
def compile_stock_video(keywords, captions, audio_path):
    print("🎞️ स्टॉक वीडियोज़ को स्क्रिप्ट के साथ जोड़ा जा रहा है...")
    audio = AudioFileClip(audio_path)
    clip_duration = audio.duration / len(keywords)
    processed_clips = []
    
    for idx, keyword in enumerate(keywords[:5]):
        base_clip = fetch_stock_video(keyword, clip_duration, idx)
        cap_text = captions[idx % len(captions)]
        if cap_text.strip():
            txt_clip = create_hindi_caption(cap_text, clip_duration).set_position(('center', 1300))
            combined = CompositeVideoClip([base_clip, txt_clip], size=(1080, 1920))
        else:
            combined = base_clip
        processed_clips.append(combined)
        
    final_video = concatenate_videoclips(processed_clips, method="compose")
    final_video = final_video.set_audio(audio).set_duration(audio.duration)
    output_name = "final_viral_production.mp4"
    final_video.write_videofile(output_name, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    
    audio.close()
    final_video.close()
    return output_name

# --- 9. YouTube अपलोड ---
def upload_video(video_file, title, description, tags):
    print("📤 YouTube पर लाइव किया जा रहा है...")
    request_body = {
        "snippet": {"categoryId": "22", "title": f"{title} #shorts", "description": description, "tags": tags},
        "status": {"privacyStatus": "public", "madeForKids": False}
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    response = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    return f"https://youtu.be/{response['id']}"

# --- मुख्य ऑटोमेशन ---
if __name__ == "__main__":
    try:
        print("👑 ULTIMATE STOCK VIDEO ENGINE ONLINE 👑")
        
        # सबसे पहले चैनल की सफाई करेगा
        clean_low_performing_videos()
        
        # वीडियो बनाएगा
        data = get_viral_script()
        asyncio.run(generate_audio(data["script"]))
        final_video = compile_stock_video(data["keywords"], data["captions"], "voice.mp3")
        
        # यूट्यूब पर अपलोड करेगा
        video_url = upload_video(final_video, data["title"], data["description"], data["tags"])
        print(f"\n🎉 सफलता! वीडियो लाइव हो गया: {video_url}")
        
        # टेलीग्राम पर सफलता का मैसेज भेजेगा
        send_telegram_report(f"✅ <b>नया वीडियो लाइव! (Stock Video)</b>\n🎬 Title: {data['title']}\n🔗 Link: {video_url}")
        
    except Exception as e:
        error_details = str(traceback.format_exc())
        print(f"\n❌ मशीन में कोई एरर आ गया:\n{error_details}")
        
        # टेलीग्राम पर एरर का मैसेज भेजेगा
        send_telegram_report(f"🚨 <b>मशीन क्रैश:</b>\n{str(e)[:300]}")
        sys.exit(1)
