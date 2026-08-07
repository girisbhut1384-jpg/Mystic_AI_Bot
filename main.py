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
import g4f
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 1. API क्रेडेंशियल्स ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, PEXELS_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ एरर: GitHub Secrets में API Keys गायब हैं!")
    sys.exit(1)

# --- 2. 30+ डायनामिक कीवर्ड्स (Keyword Rotation) ---
TECH_KEYWORDS = [
    "hacker typing", "neon server", "cyber security", "matrix code", "dark web", 
    "data center", "abstract tech", "glitch", "ai brain", "future technology",
    "circuit board", "smartphone close up", "code scrolling", "server room", 
    "digital network", "hacking", "cyberpunk city", "neon lights", "binary code",
    "artificial intelligence", "robot face", "hologram", "data transfer", 
    "virtual reality", "satellite space", "mysterious tech", "computer virus",
    "fingerprint scan", "digital eye", "tech background", "motherboard", "fiber optics"
]

# --- 3. स्क्रिप्ट जनरेशन (Smooth Ending & CTA) ---
def get_viral_script():
    print("🧠 AI से नई कहानी और CTA लिखी जा रही है...")
    topics = ["साइबर सिक्योरिटी", "आर्टिफिशियल इंटेलिजेंस", "डीप वेब", "अंतरिक्ष रहस्य", "भविष्य की तकनीक"]
    
    prompt = f"""Write a mystery tech script about '{random.choice(topics)}' for a 45-second YouTube Short. Hindi language. 
    IMPORTANT: The script MUST end with a strong Call to Action (CTA) like 'सब्सक्राइब करें' or 'लाइक करें'.
    Return ONLY a JSON with keys: 
    'title', 'description', 'tags', 
    'script' (Hindi narration with CTA at the end), 
    'captions' (array of 5 short Hindi phrases), 
    'keywords' (array of 5 English search terms from tech background)."""
    
    try:
        response = g4f.ChatCompletion.create(model=g4f.models.gpt_35_turbo, messages=[{"role": "user", "content": prompt}])
        content = response.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print("⚠️ AI फेल, बैकअप स्क्रिप्ट का उपयोग...")
        return {
            "title": "इंटरनेट का काला सच! 😱 #shorts",
            "description": "इंटरनेट के रहस्य! #mystery #hacker #tech",
            "tags": ["mystery", "hacker", "tech", "shorts"],
            "script": "इंटरनेट की दुनिया जितनी साफ़ दिखती है, अंदर से उतनी ही खौफनाक है। हर सेकंड कोई बड़ा सर्वर हैक हो रहा है। अपनी जानकारी सुरक्षित रखें। ऐसे ही रहस्य जानने के लिए अभी सब्सक्राइब करें!",
            "captions": ["इंटरनेट का काला सच", "सर्वर हैक", "डेटा चोरी", "भयानक रहस्य", "अभी सब्सक्राइब करें"],
            "keywords": ["hacker typing", "neon server", "cyber security", "matrix code", "data center"]
        }

# --- 4. आवाज़ और बैकग्राउंड म्यूजिक (BGM) ---
async def generate_audio(text):
    print("🎙️ आवाज़ तैयार हो रही है...")
    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
    await communicate.save("voice.mp3")
    
    main_audio = AudioFileClip("voice.mp3")
    
    # BGM लॉजिक (अगर bgm.mp3 फाइल मौजूद है तो मिक्स करेगा)
    if os.path.exists("bgm.mp3"):
        print("🎵 बैकग्राउंड म्यूजिक जोड़ा जा रहा है...")
        bg_audio = AudioFileClip("bgm.mp3").volumex(0.15) # वॉल्यूम कम रखें
        # BGM को लूप करें ताकि वह मेन आवाज़ जितना लंबा हो जाए
        from moviepy.audio.fx.all import audio_loop
        bg_audio = audio_loop(bg_audio, duration=main_audio.duration)
        final_audio = CompositeAudioClip([main_audio, bg_audio])
        return final_audio, main_audio.duration
    
    return main_audio, main_audio.duration

# --- 5. Pexels से वीडियो (No Black Screen & Video Slicing) ---
def fetch_stock_video(duration):
    keyword = random.choice(TECH_KEYWORDS)
    print(f"📥 Pexels से '{keyword}' के लिए वीडियो ढूँढ रहे हैं...")
    
    # रैंडम पेज (Random Page Selection)
    page = random.randint(1, 5) 
    url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&per_page=15&page={page}&orientation=portrait"
    
    try:
        response = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=15)
        if response.status_code == 200 and response.json().get("videos"):
            video = random.choice(response.json()["videos"])
            video_files = sorted(video["video_files"], key=lambda x: x['width'] * x['height'], reverse=True)
            video_url = video_files[0]["link"]
            
            temp_name = f"temp_vid_{random.randint(1,999)}.mp4"
            urllib.request.urlretrieve(video_url, temp_name)
            
            clip = VideoFileClip(temp_name).without_audio()
            
            # वीडियो स्लाइसिंग (Video Slicing) 5 से 10 सेकंड
            if clip.duration > duration + 1:
                start_time = random.uniform(0, clip.duration - duration - 1)
                clip = clip.subclip(start_time, start_time + duration)
            else:
                repeats = int(duration / clip.duration) + 1
                clip = concatenate_videoclips([clip] * repeats).subclip(0, duration)
                
            clip = clip.resize(height=1920)
            clip = clip.crop(x_center=clip.w/2, y_center=1920/2, width=1080, height=1920)
            return clip
    except Exception as e:
        print(f"⚠️ Pexels फेल हुआ: {e}")
    
    # अगर Pexels फेल हो जाए तो एरर से बचने के लिए एक डमी क्लिप (काला पर्दा नहीं, रंगीन पर्दा)
    img = Image.new('RGB', (1080, 1920), color=(10, 30, 50))
    img.save("safe_fallback.jpg")
    return ImageClip("safe_fallback.jpg").set_duration(duration)

# --- 6. सबटाइटल पोज़िशनिंग और स्टाइल (Center & Stroke) ---
def create_subtitle_clip(text, duration):
    canvas_w, canvas_h = 1080, 1920  # पूरे स्क्रीन का साइज़
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_path = "Yantramanav-Black.ttf"
    if not os.path.exists(font_path):
        try:
            urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/yantramanav/Yantramanav-Black.ttf", font_path)
        except: pass
    
    try: font = ImageFont.truetype(font_path, 140) 
    except: font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text, width=12)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    
    # सेंटर में रखना (या थोड़ा नीचे: y = 1920 * 0.65 ताकि UI से बचे)
    x = (canvas_w - (bbox[2] - bbox[0])) // 2
    y = int(canvas_h * 0.65) - (bbox[3] - bbox[1]) // 2 
    
    # ब्लैक स्ट्रोक / आउटलाइन
    stroke_width = 15
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFE81F", stroke_width=stroke_width, stroke_fill="black", align='center')
    
    temp_name = f"cap_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 7. फाइनल वीडियो संपादन ---
def compile_final_video(captions, final_audio, audio_duration):
    print("🎞️ वीडियो, ऑडियो और सबटाइटल्स जोड़े जा रहे हैं...")
    
    # 2-सेकंड का बफर जोड़ना (ताकि वीडियो अचानक न कटे)
    total_video_duration = audio_duration + 2.0 
    clip_duration = total_video_duration / len(captions)
    processed_clips = []
    
    for idx, cap_text in enumerate(captions):
        base_clip = fetch_stock_video(clip_duration)
        
        if cap_text.strip():
            # सबटाइटल को स्क्रीन पर डालना
            txt_clip = create_subtitle_clip(cap_text, clip_duration)
            combined = CompositeVideoClip([base_clip, txt_clip], size=(1080, 1920))
        else:
            combined = base_clip
            
        processed_clips.append(combined)
        
    final_video = concatenate_videoclips(processed_clips, method="compose")
    # ऑडियो को वीडियो पर सेट करना
    final_video = final_video.set_audio(final_audio).set_duration(total_video_duration)
    
    output_name = "final_viral_shorts.mp4"
    final_video.write_videofile(output_name, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    return output_name

# --- 8. YouTube अपलोड ---
def upload_video(video_file, title, description, tags):
    print("📤 YouTube पर अपलोड हो रहा है...")
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    youtube = build("youtube", "v3", credentials=creds)
    
    request_body = {
        "snippet": {"categoryId": "22", "title": f"{title}", "description": description, "tags": tags},
        "status": {"privacyStatus": "public", "madeForKids": False}
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    res = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    return f"https://youtu.be/{res['id']}"

def send_telegram_report(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})
    except: pass

if __name__ == "__main__":
    try:
        data = get_viral_script()
        final_audio, audio_duration = asyncio.run(generate_audio(data["script"]))
        
        final_video = compile_final_video(data["captions"], final_audio, audio_duration)
        video_url = upload_video(final_video, data["title"], data["description"], data["tags"])
        
        send_telegram_report(f"✅ <b>नया शॉर्ट्स लाइव!</b>\n🎬 {data['title']}\n🔗 {video_url}")
        print("🎉 सब कुछ सफलतापूर्वक हो गया!")
        
    except Exception as e:
        err = str(traceback.format_exc())
        send_telegram_report(f"🚨 <b>मशीन क्रैश:</b>\n{err[:300]}")
        sys.exit(1)
