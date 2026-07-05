import os
import sys
import requests
import time
import random
import textwrap
import json
import urllib.request
import traceback
from openai import OpenAI
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFont

if not hasattr(Image, 'Resampling'):
    Image.Resampling = getattr(Image, 'LANCZOS', 1)
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ImageClip
from moviepy.video.fx.all import loop 

# --- 1. प्रीमियम API क्रेडेंशियल्स ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY")
LEONARDO_KEY = os.environ.get("LEONARDO_KEY")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, OPENAI_KEY, ELEVEN_KEY, LEONARDO_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ एरर: कोई प्रीमियम चाबी या टेलीग्राम टोकन गायब है! कृपया GitHub Secrets चेक करें।")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_KEY)

# --- 2. टेलीग्राम रिपोर्ट और सर्वर स्टेटस फंक्शन्स ---
def send_telegram_report(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except:
        pass

def check_ram_usage():
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        total_ram = int(lines[0].split()[1]) / 1024 / 1024 
        available_ram = int(lines[2].split()[1]) / 1024 / 1024 
        used_ram = total_ram - available_ram
        return f"सर्वर रैम (RAM) उपयोग: {used_ram:.2f} GB / {total_ram:.2f} GB"
    except:
        return "सर्वर रैम (RAM): डेटा उपलब्ध नहीं"

def check_elevenlabs_credits():
    try:
        url = "https://api.elevenlabs.io/v1/user/subscription"
        headers = {"xi-api-key": ELEVEN_KEY}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            remain = data['character_limit'] - data['character_count']
            return f"ElevenLabs: {remain} कैरेक्टर्स बाकी"
        return "ElevenLabs: क्रेडिट अनुपलब्ध"
    except: 
        return "ElevenLabs: चेक विफल"

def check_leonardo_credits():
    try:
        url = "https://cloud.leonardo.ai/api/rest/v1/me"
        headers = {"accept": "application/json", "authorization": f"Bearer {LEONARDO_KEY}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            remain = res.json().get('user_details', [{}])[0].get('api_credit_volume', 'N/A')
            return f"Leonardo: {remain} टोकन्स बाकी"
        return "Leonardo: क्रेडिट अनुपलब्ध"
    except: 
        return "Leonardo: चेक विफल"

# --- 3. सुपर वायरल स्क्रिप्ट जनरेशन (GPT-4o) ---
def get_viral_content():
    print("🧠 GPT-4o से एकदम अनसुनी स्क्रिप्ट लिखी जा रही है...")
    master_prompt = """
    Write an ULTRA-VIRAL, high-retention 45-50 second YouTube Short script about a RARE, UNHEARD-OF and mind-blowing space or historical mystery in Hindi.
    STRICT RULES:
    1. NO FLUFF: The mystery must be factually accurate, highly obscure, and actively increase knowledge.
    2. HOOK: First 3 seconds MUST be a brutal pattern interrupt.
    3. CTA: The last sentence MUST be EXACTLY: "हमारे चैनल को सब्सक्राइब करें और पूरा सच जानने व ऐसे ही रहस्यों को अनलॉक करने के लिए, डिस्क्रिप्शन में दिए गए लिंक पर क्लिक करें।"
    4. Return ONLY valid JSON: {"title": "", "description": "", "tags": [], "script": "", "captions": [], "prompts": []}
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": master_prompt}],
        response_format={"type": "json_object"},
        temperature=0.85
    )
    parsed = json.loads(response.choices[0].message.content)
    tokens_used = response.usage.total_tokens
    return (
        parsed["title"], parsed["description"], parsed["tags"],
        parsed["script"].replace("*", ""), parsed["prompts"][:6], parsed["captions"][:6], tokens_used
    )

# --- 4. प्रीमियम वॉयसओवर (ElevenLabs) ---
def generate_premium_audio(script):
    print("🎙️ ElevenLabs से डीप सस्पेंस वॉइसओवर बन रहा है...")
    voice_id = "21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    data = {"text": script, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.35, "similarity_boost": 0.85, "style": 0.1}}
    
    res = requests.post(url, json=data, headers=headers)
    if res.status_code != 200:
        raise Exception(f"ElevenLabs ऑडियो एरर: {res.text}")
        
    audio_path = "voice.mp3"
    with open(audio_path, "wb") as f:
        f.write(res.content)
    return audio_path

# --- 5. लियोनार्डो इमेज इंजन (No Runway) ---
def generate_premium_videos(prompts):
    image_files = []
    leo_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    leo_headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Bearer {LEONARDO_KEY}"}
    
    for i, p in enumerate(prompts):
        fname = f"clip_{i}.jpg"
        print(f"\n🎨 [लियोनार्डो] दृश्य {i+1} तैयार हो रहा है...")
        
        payload = {
            "height": 1024, "width": 512, 
            "prompt": p + ", masterpiece, hyper-realistic, dark cinematic lighting, 8k", 
            "modelId": "6bef9f1b-29cb-40c7-b935-c3230a109968"
        }
        res = requests.post(leo_url, json=payload, headers=leo_headers)
        if res.status_code != 200:
            raise Exception(f"Leonardo API एरर: {res.text}")
            
        gen_id = res.json()["sdGenerationJob"]["generationId"]
        
        for _ in range(15):
            time.sleep(10)
            check = requests.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}", headers=leo_headers)
            if check.json()["generations_by_pk"]["status"] == "COMPLETE":
                img_url = check.json()["generations_by_pk"]["generated_images"][0]["url"]
                break
        
        with open(fname, "wb") as f: f.write(requests.get(img_url).content)
        image_files.append(fname)
        print(f"✅ दृश्य {i+1} सफलता से सेव हो गया!")
            
    return image_files

# --- 6. डायनामिक बोल्ड कैप्शंस ---
def create_bold_yellow_caption(text, duration):
    img = Image.new('RGBA', (1080, 400), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = "Roboto-Black.ttf"
    if not os.path.exists(font_path):
        urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/apache/roboto/Roboto-Black.ttf", font_path)
    
    font = ImageFont.truetype(font_path, 140)
    draw.multiline_text((540, 200), textwrap.fill(text.upper(), 14), font=font, fill="#FFE81F", stroke_width=18, stroke_fill="black", anchor="mm", align='center')
    img.save("temp.png")
    return ImageClip("temp.png").set_duration(duration)

# --- 7. हाई-रिटेंशन रेंडरिंग (मोशन ज़ूम के साथ) ---
def compile_high_retention_video(img_files, captions, audio_path):
    print("🎞️ वीडियो रेंडर किया जा रहा है...")
    audio = AudioFileClip(audio_path)
    dur = audio.duration / len(img_files)
    processed_clips = []
    
    for i, ifile in enumerate(img_files):
        # मोशन ज़ूम इफ़ेक्ट (इमेज को ही वीडियो बना दिया)
        clip = ImageClip(ifile).set_duration(dur).resize(newsize=(1080, 1920)).resize(lambda t: 1 + 0.05 * t)
        txt = create_bold_yellow_caption(captions[i % len(captions)], dur).set_position(('center', 0.75), relative=True)
        combined = CompositeVideoClip([clip, txt], size=(1080, 1920))
        processed_clips.append(combined)
        
    final = concatenate_videoclips(processed_clips, method="compose").set_audio(audio)
    final.write_videofile("final_viral_production.mp4", fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)
    return "final_viral_production.mp4"

# --- 8. यूट्यूब अपलोड ---
def upload_to_youtube(video_file, title, description, tags):
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    youtube = build("youtube", "v3", credentials=creds)
    body = {"snippet": {"title": title, "description": description, "tags": tags, "categoryId": "22"}, "status": {"privacyStatus": "public"}}
    res = youtube.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(video_file)).execute()
    return f"https://youtu.be/{res['id']}"

if __name__ == "__main__":
    try:
        data = get_viral_content()
        imgs = generate_premium_videos(data['prompts']) # Leonardo Images
        vid = compile_high_retention_video(imgs, data['captions'], generate_premium_audio(data['script']))
        link = upload_to_youtube(vid, data['title'], data['description'], data['tags'])
        
        report = f"✅ <b>वीडियो लाइव:</b> {link}\n{check_ram_usage()}\n{check_elevenlabs_credits()}\n{check_leonardo_credits()}"
        send_telegram_report(report)
    except Exception as e:
        send_telegram_report(f"❌ क्रैश रिपोर्ट: {str(e)}")
