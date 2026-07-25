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

from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips, CompositeVideoClip, ImageClip

# --- 1. प्रीमियम API क्रेडेंशियल्स ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY")
HF_TOKEN = os.environ.get("HUGGINGFACE_TOKEN") # 👈 असली फ्री वीडियो के लिए नया टोकन
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, OPENAI_KEY, ELEVEN_KEY, HF_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ एरर: कोई सीक्रेट की (Key) गायब है! (HUGGINGFACE_TOKEN चेक करें)")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_KEY)
creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
youtube = build("youtube", "v3", credentials=creds)

def send_telegram_report(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})
    except: pass

# --- 2. 🤖 ऑटो-डिलीट सिस्टम ---
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
    except Exception as e:
        pass

# --- 3. वायरल स्क्रिप्ट जनरेशन (💥 हर बार नई कहानी) ---
def get_viral_content():
    print("🧠 GPT-4o से बिल्कुल नई स्क्रिप्ट लिखी जा रही है...")
    
    # 👈 रैंडम टॉपिक जनरेटर ताकि वीडियो कभी रिपीट न हो
    topics = [
        "Deep Ocean Unexplained Mysteries", 
        "Ancient Lost Technologies", 
        "Creepy Space Voids and Black Holes", 
        "Unsolved Historical Disappearances", 
        "Bizarre Scientific Discoveries on Earth",
        "Secret Underground Civilizations"
    ]
    selected_topic = random.choice(topics)
    print(f"🎯 आज का नया टॉपिक: {selected_topic}")
    
    master_prompt = f"""
    Write a HYPER-VIRAL mystery script in Hindi (45-50 seconds) specifically about this exact topic: '{selected_topic}'.
    Make it completely unique. DO NOT use the Wow Signal.
    
    CRITICAL RULES FOR SCRIPT:
    1. ONLY write the exact words the narrator will speak. NO stage directions.
    2. Ensure Hindi is engaging, mysterious, and fast-paced.
    
    Return ONLY JSON format:
    {{"title": "Viral Hindi Title Here 🔥", "description": "SEO Desc...", "tags": ["mystery", "space", "viral"], "script": "Raw spoken Hindi text only...", "captions": ["PUNCHY 1", "PUNCHY 2", "PUNCHY 3", "PUNCHY 4", "PUNCHY 5", "PUNCHY 6"], "prompts": ["Visual matching part 1", "Visual matching part 2", "Visual matching part 3", "Visual matching part 4", "Visual matching part 5", "Visual matching part 6"]}}
    """
    response = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": master_prompt}], response_format={"type": "json_object"}
    )
    parsed = json.loads(response.choices[0].message.content)
    return parsed["title"], parsed["description"], parsed["tags"], parsed["script"], parsed["prompts"][:6], parsed["captions"][:6]

def generate_premium_audio(script):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    res = requests.post(url, json={"text": script, "model_id": "eleven_multilingual_v2"}, headers=headers)
    with open("voice.mp3", "wb") as f: f.write(res.content)
    return "voice.mp3"

# --- 4. असली फ्री वीडियो AI (Hugging Face SVD) ---
def generate_free_real_videos(prompts):
    video_files = []
    print("\n🎨 [100% FREE AI] पहले फोटो बन रही है, फिर उसे असली वीडियो में बदला जाएगा...")
    
    hf_api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-img2vid-xt"
    hf_headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    for i, p in enumerate(prompts):
        img_name = f"scene_{i}.jpg"
        vid_name = f"scene_video_{i}.mp4"
        
        # 1. Pollinations से शानदार फोटो डाउनलोड करें
        safe_prompt = urllib.parse.quote(p + ", 8k resolution, cinematic, photorealistic")
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920&nologo=true"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(img_name, 'wb') as out_file:
            out_file.write(response.read())
            
        print(f"📥 दृश्य {i+1} की फोटो तैयार। अब असली वीडियो बन रहा है (इसमें समय लग सकता है)...")
        
        # 2. Hugging Face से फोटो को असली वीडियो में बदलें (Image-to-Video)
        with open(img_name, "rb") as f:
            img_data = f.read()
            
        success = False
        for attempt in range(4): # HF फ्री API कभी-कभी लोड होने में समय लेती है
            res = requests.post(hf_api_url, headers=hf_headers, data=img_data)
            if res.status_code == 200:
                with open(vid_name, "wb") as f:
                    f.write(res.content)
                video_files.append(vid_name)
                print(f"✅ दृश्य {i+1} का असली AI वीडियो बन गया!")
                success = True
                break
            elif "loading" in res.text.lower():
                print("⏳ AI सर्वर वार्म-अप हो रहा है, 20 सेकंड रुकें...")
                time.sleep(20)
            else:
                time.sleep(10)
                
        # अगर फ्री API बहुत ज्यादा बिजी हो (बैकअप सिस्टम ताकि मशीन क्रैश न हो)
        if not success:
            print(f"⚠️ फ्री वीडियो AI ओवरलोड है। इस क्लिप के लिए स्मार्ट मोशन बैकअप का उपयोग कर रहे हैं...")
            video_files.append(img_name) 
            
    return video_files

# --- 5. 💥 स्पेशल हिंदी फॉन्ट और सही साइज (डब्बे फिक्स) ---
def create_hindi_caption(text, duration):
    canvas_w, canvas_h = 1080, 500
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 👈 नया हिंदी (देवनागरी) सपोर्टेड फॉन्ट ताकि डब्बे न बनें
    font_path = "Yantramanav-Black.ttf"
    if not os.path.exists(font_path):
        try:
            font_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/yantramanav/Yantramanav-Black.ttf"
            req = urllib.request.Request(font_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(font_path, 'wb') as out_file:
                out_file.write(response.read())
        except Exception as e:
            pass
    
    # फॉन्ट का साइज़ 120 सेट किया है ताकि अक्षर बहुत बड़े भी रहें और स्क्रीन से बाहर भी न जाएं
    try: font = ImageFont.truetype(font_path, 120) 
    except: font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text, width=15)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    x = (canvas_w - (bbox[2] - bbox[0])) // 2
    y = (canvas_h - (bbox[3] - bbox[1])) // 2
    
    draw.multiline_text((x+8, y+8), wrapped, font=font, fill="black", align='center')
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFE81F", stroke_width=18, stroke_fill="black", align='center')
    
    temp_name = f"cap_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 6. रेंडरिंग ---
def compile_viral_video(media_files, captions, audio_path):
    print("🎞️ फाइनल वायरल वीडियो तैयार किया जा रहा है...")
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration
    clip_duration = audio_duration / len(media_files)
    processed_clips = []
    
    for idx, file_path in enumerate(media_files):
        if file_path.endswith('.mp4'):
            # अगर HF से असली वीडियो बना है
            base_clip = VideoFileClip(file_path)
            # वीडियो को क्लिप ड्यूरेशन के हिसाब से लूप या कट करें
            if base_clip.duration < clip_duration:
                base_clip = base_clip.fx(vfx.loop, duration=clip_duration)
            else:
                base_clip = base_clip.subclip(0, clip_duration)
            base_clip = base_clip.resize(newsize=(1080, 1920))
        else:
            # बैकअप अगर API बिजी थी तो स्मार्ट मोशन इफ़ेक्ट
            base_clip = ImageClip(file_path).set_duration(clip_duration)
            base_clip = base_clip.resize(lambda t: 1 + 0.10 * (t / clip_duration)) 
            base_clip = base_clip.set_position(('center', 'center')).resize(newsize=(1080, 1920))
        
        cap_text = captions[idx % len(captions)]
        if cap_text.strip():
            txt_clip = create_hindi_caption(cap_text, clip_duration)
            txt_clip = txt_clip.set_position(('center', 1250)) # टेक्स्ट सुरक्षित रूप से नीचे
            combined = CompositeVideoClip([base_clip, txt_clip], size=(1080, 1920))
        else:
            combined = base_clip
            
        processed_clips.append(combined)
        
    final_video = concatenate_videoclips(processed_clips, method="compose")
    final_video = final_video.set_audio(audio).set_duration(audio_duration)
    
    output_name = "final_viral_production.mp4"
    final_video.write_videofile(output_name, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    
    audio.close()
    final_video.close()
    return output_name

# --- 7. यूट्यूब अपलोड ---
def upload_to_youtube(video_file, title, description, tags):
    print("📤 YouTube पर लाइव किया जा रहा है...")
    request_body = {
        "snippet": {"categoryId": "22", "title": f"{title} #shorts", "description": description, "tags": tags},
        "status": {"privacyStatus": "public", "madeForKids": False}
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    
    response = None
    for retry in range(5):
        try:
            response = request.execute()
            break
        except Exception as e:
            time.sleep(5)
            
    if response is None:
        raise Exception("अपलोड फेल हो गया।")
        
    return f"https://youtu.be/{response.get('id')}"

if __name__ == "__main__":
    try:
        print("👑 TITAN AUTOMATION ENGINE (REAL AI VIDEO & HINDI FIX) ONLINE 👑")
        
        clean_low_performing_videos()
        
        title, description, tags, script, prompts, captions = get_viral_content()
        audio_path = generate_premium_audio(script)
        
        # 👈 नया असली वीडियो इंजन
        media_files = generate_free_real_videos(prompts) 
        
        final_output = compile_viral_video(media_files, captions, audio_path)
        
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
