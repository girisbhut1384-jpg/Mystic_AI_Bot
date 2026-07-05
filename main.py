import os
import sys
import requests
import time
import random
import textwrap
import json
import urllib.request
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

# --- 1. प्रीमियम API क्रेडेंशियल्स ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY")
LEONARDO_KEY = os.environ.get("LEONARDO_API_KEY")
RUNWAY_KEY = os.environ.get("RUNWAYML_API_SECRET")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, OPENAI_KEY, ELEVEN_KEY, LEONARDO_KEY, RUNWAY_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ एरर: कोई प्रीमियम चाबी या टेलीग्राम टोकन गायब है! कृपया GitHub Secrets चेक करें।")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_KEY)

# --- 2. टेलीग्राम रिपोर्ट और क्रेडिट चेक ---
def send_telegram_report(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"टेलीग्राम मैसेज एरर: {e}")

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
    3. PACING: Exactly 110-120 words in Hindi for a 45-50 second delivery.
    4. CTA: The last sentence MUST be EXACTLY: "हमारे चैनल को सब्सक्राइब करें और पूरा सच जानने व ऐसे ही रहस्यों को अनलॉक करने के लिए, डिस्क्रिप्शन में दिए गए लिंक पर क्लिक करें।"
    5. PROMPTS: Provide 6 ultra-realistic image prompts. Keywords: "hyper-realistic, cinematic lighting, eerie, 8k".
    6. CAPTIONS: Provide 6 short, punchy 2-3 word phrases for on-screen captions matching the story.
    
    Return ONLY valid JSON format:
    {
      "title": "Viral Title Here 🔥",
      "description": "SEO Description...",
      "tags": ["mystery", "space", "viral", "unheard story", "education"],
      "script": "Complete Hindi script...",
      "captions": ["PUNCHY PHRASE 1", "PUNCHY PHRASE 2", "PUNCHY PHRASE 3", "PUNCHY PHRASE 4", "PUNCHY PHRASE 5", "PUNCHY PHRASE 6"],
      "prompts": ["Visual prompt 1", "Visual prompt 2", "Visual prompt 3", "Visual prompt 4", "Visual prompt 5", "Visual prompt 6"]
    }
    """
    try:
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
    except Exception as e:
        send_telegram_report(f"❌ <b>GPT-4o एरर:</b> {e}")
        sys.exit(1)

# --- 4. प्रीमियम वॉयसओवर (ElevenLabs) ---
def generate_premium_audio(script):
    print("🎙️ ElevenLabs से डीप सस्पेंस वॉइसओवर बन रहा है...")
    voice_id = "21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    data = {"text": script, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.35, "similarity_boost": 0.85, "style": 0.1}}
    
    res = requests.post(url, json=data, headers=headers)
    if res.status_code != 200:
        send_telegram_report("❌ <b>ElevenLabs एरर:</b> ऑडियो जनरेट नहीं हुआ।")
        sys.exit(1)
        
    audio_path = "voice.mp3"
    with open(audio_path, "wb") as f:
        f.write(res.content)
    return audio_path

# --- 5. हॉलीवुड-ग्रेड विजुअल्स (Strict Paid Mode + Smart Downloader Fix) ---
def generate_premium_videos(prompts):
    video_clips = []
    leo_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    leo_headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Bearer {LEONARDO_KEY}"}
    
    runway_url = "https://api.dev.runwayml.com/v1/image_to_video"
    runway_headers = {"Authorization": f"Bearer {RUNWAY_KEY}", "X-Runway-Version": "2024-11-06", "Content-Type": "application/json"}
    
    for i, p in enumerate(prompts):
        vname = f"clip_{i}.mp4"
        print(f"\n🎨 [लियोनार्डो] दृश्य {i+1} तैयार हो रहा है...")
        
        try:
            payload = {
                "height": 1024, 
                "width": 512, 
                "prompt": p + ", masterpiece, hyper-realistic, dark cinematic lighting, 8k", 
                "num_images": 1
            }
            res = requests.post(leo_url, json=payload, headers=leo_headers)
            if res.status_code != 200:
                raise Exception(f"Leonardo Error: {res.text}")
                
            gen_id = res.json()["sdGenerationJob"]["generationId"]
            
            img_url = None
            for _ in range(12):
                time.sleep(10)
                check = requests.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}", headers=leo_headers)
                if check.json()["generations_by_pk"]["status"] == "COMPLETE":
                    img_url = check.json()["generations_by_pk"]["generated_images"][0]["url"]
                    break
            
            if not img_url:
                raise Exception("Leonardo Timeout")

            print(f"🎬 [रनवे एमएल] मोशन वीडियो बन रहा है (Strict Mode)...")
            runway_payload = {
                "model": "gen3a_turbo",
                "promptImage": img_url,
                "promptText": "slow cinematic camera zoom in, eerie atmospheric smoke movement, highly realistic",
                "duration": 5
            }
            
            r_res = requests.post(runway_url, json=runway_payload, headers=runway_headers)
            if r_res.status_code not in [200, 201]:
                raise Exception(f"Runway Server Issue: {r_res.text}")
                
            task_id = r_res.json()["id"]
            
            final_video_url = None
            for _ in range(30): 
                time.sleep(10)
                check_url = f"https://api.dev.runwayml.com/v1/tasks/{task_id}"
                r_check = requests.get(check_url, headers=runway_headers)
                
                if r_check.status_code == 200:
                    status = r_check.json()["status"]
                    if status == "SUCCEEDED":
                        final_video_url = r_check.json()["output"][0]
                        break
                    elif status == "FAILED":
                        raise Exception("Runway Task Failed Internally")
            
            if final_video_url:
                print(f"📥 वीडियो डाउनलोड किया जा रहा है...")
                vid_res = requests.get(final_video_url, stream=True)
                if vid_res.status_code == 200:
                    with open(vname, "wb") as f:
                        for chunk in vid_res.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
                    
                    if os.path.getsize(vname) < 10000:
                        raise Exception("Runway से करप्ट (0 Byte) फाइल डाउनलोड हुई है।")
                        
                    video_clips.append(vname)
                    print(f"✅ Runway मोशन वीडियो {i+1} सफलता से डाउनलोड और सुरक्षित हो गया!")
                else:
                    raise Exception(f"Runway वीडियो डाउनलोड फेल (Status: {vid_res.status_code})")
            else:
                raise Exception("Runway Timeout - वीडियो समय पर नहीं बना")
                
        except Exception as main_error:
            error_msg = f"❌ <b>विजुअल क्रैश:</b> दृश्य {i+1} में गड़बड़ी आई। क्वालिटी से समझौता न करने के लिए प्रोसेस रोक दिया गया है। एरर: {main_error}"
            send_telegram_report(error_msg)
            sys.exit(1)
            
    return video_clips

# --- 6. डायनामिक बोल्ड कैप्शंस ---
def create_bold_yellow_caption(text, duration):
    canvas_w, canvas_h = 1080, 400
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_path = "Roboto-Black.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Black.ttf"
            urllib.request.urlretrieve(url, font_path)
        except Exception as e:
            print(f"⚠️ फॉन्ट डाउनलोड एरर: {e}")
    
    try:
        font = ImageFont.truetype(font_path, 140)
    except:
        font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text.upper(), width=14)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    x, y = (canvas_w - text_w) // 2, (canvas_h - text_h) // 2
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFE81F", stroke_width=18, stroke_fill="black", align='center')
    
    temp_name = f"cap_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 7. हाई-रिटेंशन रेंडरिंग इंजन (Memory Safe Loop Fix) ---
def compile_high_retention_video(video_files, captions, audio_path):
    print("🎞️ वीडियो रेंडर किया जा रहा है (मेमोरी सेफ लूप फिक्स के साथ)...")
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration
    
    clip_duration = audio_duration / len(video_files)
    processed_clips = []
    
    for idx, vfile in enumerate(video_files):
        clip = VideoFileClip(vfile)
        
        # 🎬 नया फिक्स: भारी 'रिवर्स' इफेक्ट की जगह सुरक्षित 'लूप' ताकि सर्वर क्रैश न हो।
        clip = concatenate_videoclips([clip, clip])
        
        clip = clip.subclip(0, min(clip_duration, clip.duration))
        clip = clip.resize(newsize=(1080, 1920))
        
        cap_text = captions[idx % len(captions)]
        if cap_text.strip():
            txt_clip = create_bold_yellow_caption(cap_text, clip.duration)
            txt_clip = txt_clip.set_position(('center', 0.75), relative=True)
            combined = CompositeVideoClip([clip, txt_clip], size=(1080, 1920))
        else:
            combined = clip
            
        if idx > 0:
            combined = combined.crossfadein(0.5)
            
        processed_clips.append(combined)
        
    final_video = concatenate_videoclips(processed_clips, padding=-0.5, method="compose")
    final_video = final_video.set_audio(audio).subclip(0, audio_duration)
    
    output_name = "final_viral_production.mp4"
    # ✅ मेमोरी बचाने के लिए preset="ultrafast" और threads=4 सेट किया है
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

if __name__ == "__main__":
    try:
        print("👑 TITAN VIRAL PRODUCTION ENGINE ONLINE (STRICT PAID MODE) 👑")
        
        title, description, tags, script, prompts, captions, gpt_tokens = get_viral_content()
        audio_path = generate_premium_audio(script)
        video_files = generate_premium_videos(prompts)
        final_output = compile_high_retention_video(video_files, captions, audio_path)
        
        gumroad_link = "https://girisbhut.gumroad.com/l/ajhzk"
        final_desc = f"{description}\n\n🚀 👉 पूरा सच जानने और ऐसे ही रहस्यों को अनलॉक करने के लिए यहाँ क्लिक करें:\n🔗 {gumroad_link}\n\n📝 Script:\n{script}"
        video_url = upload_to_youtube(final_output, title, final_desc, tags)
        
        elevenlabs_status = check_elevenlabs_credits()
        leonardo_status = check_leonardo_credits()
        
        report_msg = f"""✅ <b>प्रीमियम वायरल वीडियो अपलोड हो गया!</b> ✅
        
🎬 <b>Title:</b> {title}
🔗 <b>YouTube Link:</b> <a href='{video_url}'>यहाँ क्लिक करके देखें</a>

📊 <b>सिस्टम स्टेटस (Strict Paid Mode):</b>
- क्वालिटी: 100% Runway AI Gen-3 Motion
- ब्लैक स्क्रीन फिक्स: मेमोरी सेफ लूप चालू 🔄
- कैप्शंस फिक्स: लार्ज 140px फॉन्ट डाउनलोड सफलता 🔠
- स्क्रिप्ट और CTA: सफलता (Subscribe + Gumroad)
- {elevenlabs_status}
- {leonardo_status}
- टोकन उपयोग (GPT-4o): {gpt_tokens}"""
        
        send_telegram_report(report_msg)
        print("✅ रिपोर्ट टेलीग्राम पर भेज दी गई है।")
        
    except Exception as e:
        error_msg = f"❌ <b>इंजन क्रैश हो गया (No Compromise Mode):</b>\nएरर: {str(e)}"
        send_telegram_report(error_msg)
        sys.exit(1)
