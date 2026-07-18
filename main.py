import os
import sys
import requests
import time
import random
import textwrap
import json
import urllib.request
import urllib.parse
import traceback
from datetime import datetime, timedelta, timezone
from openai import OpenAI
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFont

# PIL Resampling Fix
if not hasattr(Image, 'Resampling'):
    Image.Resampling = getattr(Image, 'LANCZOS', 1)
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import AudioFileClip, concatenate_videoclips, CompositeVideoClip, ImageClip

# --- 1. प्रीमियम API क्रेडेंशियल्स ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, OPENAI_KEY, ELEVEN_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ एरर: कोई सीक्रेट की (Key) गायब है!")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_KEY)
creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
youtube = build("youtube", "v3", credentials=creds)

def send_telegram_report(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})
    except: pass

# --- 2. 🤖 ऑटो-डिलीट सिस्टम (7 दिन पुराने, < 100 व्यूज वाले फ्लॉप वीडियो) ---
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
                        print(f"🗑️ डिलीट कर रहे हैं वीडियो ID: {video_id} (Views: {views})")
                        youtube.videos().delete(id=video_id).execute()
                        deleted_count += 1
                        time.sleep(1)
                        
        if deleted_count > 0:
            send_telegram_report(f"🧹 <b>चैनल क्लीनअप:</b> {deleted_count} फ्लॉप वीडियो डिलीट किए गए।")
        else:
            print("✅ चैनल एकदम क्लीन है, कोई फ्लॉप वीडियो नहीं मिला।")
    except Exception as e:
        print(f"⚠️ क्लीनअप एरर: {str(e)}")

# --- 3. वायरल स्क्रिप्ट जनरेशन ---
def get_viral_content():
    print("🧠 GPT-4o से स्क्रिप्ट लिखी जा रही है...")
    master_prompt = """
    Write a HYPER-VIRAL space or historical mystery script in Hindi.
    Return ONLY JSON:
    {
      "title": "Title Here 🔥",
      "description": "SEO Desc...",
      "tags": ["mystery", "space"],
      "script": "Complete text...",
      "captions": ["PUNCHY 1", "PUNCHY 2", "PUNCHY 3", "PUNCHY 4", "PUNCHY 5", "PUNCHY 6"],
      "prompts": ["Visual prompt 1", "Visual prompt 2", "Visual prompt 3", "Visual prompt 4", "Visual prompt 5", "Visual prompt 6"]
    }
    """
    response = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": master_prompt}], response_format={"type": "json_object"}
    )
    parsed = json.loads(response.choices[0].message.content)
    return parsed["title"], parsed["description"], parsed["tags"], parsed["script"], parsed["prompts"][:6], parsed["captions"][:6]

def generate_premium_audio(script):
    print("🎙️ ElevenLabs से सस्पेंस वॉइसओवर बन रहा है...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    res = requests.post(url, json={"text": script, "model_id": "eleven_multilingual_v2"}, headers=headers)
    with open("voice.mp3", "wb") as f: f.write(res.content)
    return "voice.mp3"

def generate_free_visuals(prompts):
    image_files = []
    print("\n🎨 [100% FREE AI] हाई-क्वालिटी इमेजेस जनरेट हो रही हैं...")
    for i, p in enumerate(prompts):
        img_name = f"scene_{i}.jpg"
        safe_prompt = urllib.parse.quote(p + ", 8k resolution, cinematic lighting, dramatic masterpiece")
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920&nologo=true"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req) as response, open(img_name, 'wb') as out_file:
            out_file.write(response.read())
        image_files.append(img_name)
        print(f"✅ दृश्य {i+1} सेव हो गया!")
        time.sleep(1)
    return image_files

# --- 4. 💥 विशाल कैप्शंस (404 Error Fixed) ---
def create_huge_caption(text, duration):
    canvas_w, canvas_h = 1080, 400
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_path = "Roboto-Black.ttf"
    if not os.path.exists(font_path):
        try:
            # नया वर्किंग लिंक (Google Fonts OFL Repo)
            url = "https://raw.githubusercontent.com/google/fonts/main/ofl/roboto/Roboto-Black.ttf"
            urllib.request.urlretrieve(url, font_path)
        except:
            try:
                # अगर पहला फेल हो जाए, तो बैकअप लिंक
                backup_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Black.ttf"
                urllib.request.urlretrieve(backup_url, font_path)
            except Exception as e:
                print(f"⚠️ फॉन्ट डाउनलोड एरर: {e}")
                pass
    
    try: font = ImageFont.truetype(font_path, 150) # 👈 विशाल फॉन्ट
    except: font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text.upper(), width=10)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    x = (canvas_w - (bbox[2] - bbox[0])) // 2
    y = (canvas_h - (bbox[3] - bbox[1])) // 2
    
    draw.multiline_text((x+5, y+5), wrapped, font=font, fill="black", align='center')
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFE81F", stroke_width=20, stroke_fill="black", align='center')
    
    temp_name = f"cap_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 5. हिल-चाल (Ken Burns Effect) और ब्लैक स्क्रीन फिक्स ---
def compile_viral_video(image_files, captions, audio_path):
    print("🎞️ वीडियो कंपाइल और मोशन इफेक्ट्स चालू (हिल-चाल के साथ)...")
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration
    clip_duration = audio_duration / len(image_files)
    processed_clips = []
    
    for idx, img_file in enumerate(image_files):
        # 🔄 ज़ूम/पैन इफेक्ट - फोटो वीडियो की तरह हिलेगी
        base_clip = ImageClip(img_file).set_duration(clip_duration)
        base_clip = base_clip.resize(lambda t: 1 + 0.08 * (t / clip_duration)) 
        base_clip = base_clip.set_position(('center', 'center')).resize(newsize=(1080, 1920))
        
        cap_text = captions[idx % len(captions)]
        if cap_text.strip():
            txt_clip = create_huge_caption(cap_text, clip_duration)
            txt_clip = txt_clip.set_position(('center', 800)) 
            combined = CompositeVideoClip([base_clip, txt_clip], size=(1080, 1920))
        else:
            combined = base_clip
            
        processed_clips.append(combined)
        
    final_video = concatenate_videoclips(processed_clips, method="compose")
    
    # 🛑 ब्लैक स्क्रीन फिक्स
    final_video = final_video.set_audio(audio).set_duration(audio_duration)
    
    output_name = "final_viral_production.mp4"
    final_video.write_videofile(output_name, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    
    audio.close()
    final_video.close()
    return output_name

# --- 6. यूट्यूब अपलोड ---
def upload_to_youtube(video_file, title, description, tags):
    print("📤 YouTube पर लाइव किया जा रहा है...")
    request_body = {
        "snippet": {"categoryId": "22", "title": f"{title} #shorts", "description": description, "tags": tags},
        "status": {"privacyStatus": "public", "madeForKids": False}
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    response = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    return f"https://youtu.be/{response.get('id')}"

if __name__ == "__main__":
    try:
        print("👑 TITAN AUTOMATION ENGINE 3.0 ONLINE 👑")
        
        clean_low_performing_videos()
        
        title, description, tags, script, prompts, captions = get_viral_content()
        audio_path = generate_premium_audio(script)
        image_files = generate_free_visuals(prompts) 
        final_output = compile_viral_video(image_files, captions, audio_path)
        
        gumroad_link = "https://girisbhut.gumroad.com/l/ajhzk"
        final_desc = f"{description}\n\n🌟 और अधिक गहराई से जानने के लिए विजिट करें:\n🔗 {gumroad_link}"
        video_url = upload_to_youtube(final_output, title, final_desc, tags)
        
        send_telegram_report(f"✅ <b>नया वीडियो लाइव!</b>\n🎬 Title: {title}\n🔗 Link: {video_url}")
        print(f"🎉 वीडियो लाइव! ID: {video_url}")
        
    except Exception as e:
        error_details = str(traceback.format_exc())
        print(f"\n❌ क्रैश हुआ:\n{error_details}")
        send_telegram_report(f"🚨 मशीन क्रैश:\n{str(e)[:300]}")
        sys.exit(1)
