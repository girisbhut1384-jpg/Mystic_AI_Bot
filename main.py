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
from openai import OpenAI
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFont

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
    print("❌ एरर: कोई प्रीमियम चाबी या टेलीग्राम टोकन गायब है!")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_KEY)

# --- 2. टेलीग्राम रिपोर्ट ---
def send_telegram_report(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, json=payload)
    except: pass

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

# --- 3. सुपर वायरल स्क्रिप्ट जनरेशन (GPT-4o) ---
def get_viral_content():
    print("🧠 GPT-4o से एकदम हाई-क्वालिटी वायरल स्क्रिप्ट लिखी जा रही है...")
    master_prompt = """
    Write a HYPER-VIRAL, high-retention 45-50 second YouTube Short script about a RARE space or historical mystery in Hindi.
    
    CRITICAL RULES FOR HIGH QUALITY:
    1. AVOID CLICHÉS: Provide SPECIFIC, deep, and mind-blowing facts.
    2. HOOK: First 3 seconds MUST be a direct, shocking question.
    3. PACING: Exactly 110-120 words in Hindi for a fast-paced delivery.
    4. CTA: Only say "ऐसे ही रहस्यों के लिए सब्सक्राइब करें।"
    5. PROMPTS (Crucial): Provide 6 ultra-detailed Midjourney-v6 style image prompts (English). Describe EXACT PHYSICAL OBJECTS. NO abstract art.
    6. CAPTIONS (Crucial): Keep ALL captions STRICTLY 1 to 3 words MAX so they appear huge on screen.
    
    Return ONLY valid JSON format:
    {
      "title": "Viral Title Here 🔥",
      "description": "SEO Description...",
      "tags": ["mystery", "space", "viral", "unheard story", "education"],
      "script": "Complete Hindi script...",
      "captions": ["PUNCHY WORD 1", "PUNCHY WORD 2", "PUNCHY WORD 3", "PUNCHY WORD 4", "PUNCHY WORD 5", "PUNCHY WORD 6"],
      "prompts": ["Specific physical visual 1", "Specific physical visual 2", "Specific physical visual 3", "Specific physical visual 4", "Specific physical visual 5", "Specific physical visual 6"]
    }
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": master_prompt}],
        response_format={"type": "json_object"},
        temperature=0.85
    )
    parsed = json.loads(response.choices[0].message.content)
    return (
        parsed["title"], parsed["description"], parsed["tags"],
        parsed["script"].replace("*", ""), parsed["prompts"][:6], parsed["captions"][:6]
    )

# --- 4. प्रीमियम वॉयसओवर (ElevenLabs) ---
def generate_premium_audio(script):
    print("🎙️ ElevenLabs से डीप सस्पेंस वॉइसओवर बन रहा है...")
    voice_id = "21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    data = {"text": script, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.35, "similarity_boost": 0.85}}
    
    res = requests.post(url, json=data, headers=headers)
    if res.status_code != 200: raise Exception(f"ElevenLabs एरर: {res.text}")
        
    audio_path = "voice.mp3"
    with open(audio_path, "wb") as f:
        f.write(res.content)
    return audio_path

# --- 5. 100% FREE हॉलीवुड-ग्रेड विजुअल्स (Pollinations AI Fixes 403) ---
def generate_free_visuals(prompts):
    image_files = []
    print("\n🎨 [100% FREE AI] हाई-क्वालिटी 8K इमेजेस जनरेट हो रही हैं (403 बाईपास के साथ)...")
    
    for i, p in enumerate(prompts):
        img_name = f"scene_{i}.jpg" 
        enhanced_prompt = p + ", ultra-realistic, highly detailed, sharp focus, cinematic lighting, 8k resolution, trending on artstation"
        safe_prompt = urllib.parse.quote(enhanced_prompt)
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920&nologo=true"
        
        print(f"📥 दृश्य {i+1} डाउनलोड किया जा रहा है...")
        
        # ✅ यहाँ 403 FORBIDDEN का पक्का इलाज (User-Agent जोड़ा गया है)
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        
        with urllib.request.urlopen(req) as response, open(img_name, 'wb') as out_file:
            out_file.write(response.read())
            
        image_files.append(img_name)
        print(f"✅ दृश्य {i+1} सफलता से सेव हो गया!")
        time.sleep(2) # सर्वर पर लोड कम करने के लिए छोटा सा गैप
            
    return image_files

# --- 6. डायनामिक बोल्ड कैप्शंस ---
def create_bold_yellow_caption(text, duration):
    canvas_w, canvas_h = 1080, 800
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_path = "Roboto-Black.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://raw.githubusercontent.com/google/fonts/main/apache/roboto/Roboto-Black.ttf"
            urllib.request.urlretrieve(url, font_path)
        except: pass
    
    try: font = ImageFont.truetype(font_path, 180) 
    except: font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text.upper(), width=9)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    x, y = (canvas_w - text_w) // 2, (canvas_h - text_h) // 2
    draw.multiline_text((x+10, y+10), wrapped, font=font, fill="black", align='center')
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFE81F", stroke_width=25, stroke_fill="black", align='center')
    
    temp_name = f"cap_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 7. हाई-रिटेंशन रेंडरिंग ---
def compile_high_retention_video(image_files, captions, audio_path):
    print("🎞️ असली वायरल वीडियो रेंडर किया जा रहा है...")
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration
    
    clip_duration = audio_duration / len(image_files)
    processed_clips = []
    
    for idx, img_file in enumerate(image_files):
        base_clip = ImageClip(img_file).set_duration(clip_duration).resize(newsize=(1080, 1920))
        
        cap_text = captions[idx % len(captions)]
        if cap_text.strip():
            txt_clip = create_bold_yellow_caption(cap_text, clip_duration)
            txt_clip = txt_clip.set_position(('center', 'center')) 
            combined = CompositeVideoClip([base_clip, txt_clip], size=(1080, 1920))
        else:
            combined = base_clip
            
        if idx > 0:
            combined = combined.crossfadein(0.5)
            
        processed_clips.append(combined)
        
    final_video = concatenate_videoclips(processed_clips, padding=-0.5, method="compose")
    final_video = final_video.set_audio(audio).subclip(0, audio_duration)
    
    output_name = "final_viral_production.mp4"
    final_video.write_videofile(output_name, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4, logger=None)
    
    audio.close()
    final_video.close()
    return output_name

# --- 8. यूट्यूब अपलोड ---
def upload_to_youtube(video_file, title, description, tags):
    print(f"📤 YouTube पर लाइव किया जा रहा है...")
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    youtube = build("youtube", "v3", credentials=creds)
    
    request_body = {
        "snippet": {"categoryId": "22", "title": f"{title} #shorts", "description": description, "tags": tags},
        "status": {"privacyStatus": "public", "madeForKids": False}
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    response = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    
    video_id = response.get("id")
    print(f"🎉 वीडियो लाइव! ID: {video_id}")
    return f"https://youtu.be/{video_id}"

# --- 9. मुख्य इंजन एक्जीक्यूशन ---
if __name__ == "__main__":
    try:
        print("👑 TITAN VIRAL PRODUCTION ENGINE (100% FREE AI) ONLINE 👑")
        title, description, tags, script, prompts, captions = get_viral_content()
        
        audio_path = generate_premium_audio(script)
        image_files = generate_free_visuals(prompts) 
        final_output = compile_high_retention_video(image_files, captions, audio_path)
        
        gumroad_link = "https://girisbhut.gumroad.com/l/ajhzk"
        final_desc = f"{description}\n\n🌟 और अधिक गहराई से जानने के लिए विजिट करें:\n🔗 {gumroad_link}"
        video_url = upload_to_youtube(final_output, title, final_desc, tags)
        
        ram_status = check_ram_usage()
        report_msg = f"""✅ <b>प्रीमियम वायरल वीडियो अपलोड हो गया! (Free AI)</b> ✅\n🎬 Title: {title}\n🔗 Link: {video_url}\n📊 {ram_status}"""
        send_telegram_report(report_msg)
        print("✅ रिपोर्ट टेलीग्राम पर भेज दी गई है।")
        
    except Exception as e:
        error_details = str(traceback.format_exc())
        
        print("\n" + "="*60)
        print("🚨🚨🚨 मशीन क्रैश हो गई! असली एरर नीचे है 🚨🚨🚨")
        print(error_details)
        print("="*60 + "\n")
        
        try:
            crash_msg = f"🚨 मशीन क्रैश 🚨\n❌ समस्या:\n{str(e)[:300]}..."
            send_telegram_report(crash_msg)
        except: pass
        
        sys.exit(1)
