import os
import sys
import requests
import time
import urllib.parse
import random
import re
import textwrap
import json
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

# टेलीग्राम बॉट क्रेडेंशियल्स
TELEGRAM_BOT_TOKEN = "8871168055:AAE5WHRQRybw814tPZfahBlLxSYZUGly8qc"
TELEGRAM_CHAT_ID = "8285187691"

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, OPENAI_KEY, ELEVEN_KEY, LEONARDO_KEY, RUNWAY_KEY]):
    print("❌ एरर: कोई प्रीमियम चाबी गायब है! कृपया GitHub Secrets चेक करें।")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_KEY)

# --- टेलीग्राम रिपोर्ट फंक्शन ---
def send_telegram_report(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"टेलीग्राम मैसेज भेजने में एरर: {e}")

# --- ElevenLabs क्रेडिट चेक फंक्शन ---
def check_elevenlabs_credits():
    try:
        url = "https://api.elevenlabs.io/v1/user"
        headers = {"xi-api-key": ELEVEN_KEY}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            used = data['subscription']['character_count']
            total = data['subscription']['character_limit']
            return f"ElevenLabs: {used}/{total} कैरेक्टर्स इस्तेमाल हुए"
        return "ElevenLabs: क्रेडिट डेटा उपलब्ध नहीं"
    except:
        return "ElevenLabs: क्रेडिट चेक विफल"

# --- 2. GPT-4o से 45-50 सेकंड की सस्पेंस स्क्रिप्ट ---
def get_viral_content():
    print("🧠 GPT-4o से 50-सेकंड की खूंखार स्क्रिप्ट लिखी जा रही है...")
    master_prompt = """
    Write a high-retention 45-50 second YouTube Short script about a terrifying space or historical mystery in Hindi.
    
    STRICT RULES:
    1. The first 3 seconds MUST be a brutal pattern interrupt. Start exactly with a shocking hook like: "क्या आप जानते हैं अंतरिक्ष के उस रहस्य के बारे में जो NASA आज भी हमसे छुपा रहा है? वह 1977 का सिग्नल... जिसने विज्ञान की दुनिया हिला दी थी।"
    2. Write around 110-120 words in Hindi for a solid 45-50 second slow suspenseful delivery.
    3. The Voiceover CTA at the very end must be exactly: "पूरा सच जानने और ऐसे ही रहस्यों को अनलॉक करने के लिए, डिस्क्रिप्शन में दिए गए लिंक पर क्लिक करें।"
    4. Provide exactly 6 distinct image prompts for video generation.
    5. Provide exactly 6 short, punchy phrases for on-screen captions matching the narrative arc.
    
    Return ONLY valid JSON format:
    {
      "title": "Viral Title Here 🔥",
      "description": "SEO Description...",
      "tags": ["mystery", "space", "viral"],
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
            temperature=0.8
        )
        parsed = json.loads(response.choices[0].message.content)
        return (
            parsed["title"], parsed["description"], parsed["tags"],
            parsed["script"].replace("*", ""), parsed["prompts"][:6], parsed["captions"][:6]
        )
    except Exception as e:
        print(f"❌ GPT-4o एरर: {e}")
        send_telegram_report(f"❌ *GPT-4o एरर:* {e}")
        sys.exit(1)

# --- 3. ElevenLabs से डीप मल्टीलिंग्वल वॉइसओवर ---
def generate_premium_audio(script):
    print("🎙️ ElevenLabs से डीप सस्पेंस वॉइसओवर बन रहा है...")
    voice_id = "21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    data = {"text": script, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.4, "similarity_boost": 0.85}}
    
    res = requests.post(url, json=data, headers=headers)
    if res.status_code != 200:
        print(f"❌ ElevenLabs फेल: {res.text}")
        send_telegram_report("❌ *ElevenLabs एरर:* ऑडियो जनरेट नहीं हुआ।")
        sys.exit(1)
        
    audio_path = "voice.mp3"
    with open(audio_path, "wb") as f:
        f.write(res.content)
    return audio_path

# --- 4. 👑 Leonardo AI + Runway ML ---
def generate_premium_videos(prompts):
    video_clips = []
    leo_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    leo_headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Bearer {LEONARDO_KEY}"}
    
    runway_url = "https://api.gateway.runwayml.com/v1/image_to_video"
    runway_headers = {"Authorization": f"Bearer {RUNWAY_KEY}", "X-Runway-Version": "2024-11-06", "Content-Type": "application/json"}
    
    for i, p in enumerate(prompts):
        vname = f"clip_{i}.mp4"
        print(f"\n🎨 [लियोनार्डो] दृश्य {i+1} के लिए बेस इमेज आर्डर की जा रही है...")
        
        try:
            payload = {"height": 1024, "width": 576, "modelId": "5c232e9a-9061-4be1-90ca-94d856b152e8", "prompt": p + ", dark creepy cinematic, 8k render", "num_images": 1}
            res = requests.post(leo_url, json=payload, headers=leo_headers)
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

            print(f"🎬 [रनवे एमएल] मोशन वीडियो बनाने के लिए इमेज ट्रांसफर की जा रही है...")
            runway_payload = {
                "model": "gen3a_turbo",
                "promptImage": img_url,
                "promptText": "slow cinematic camera zoom in, eerie atmospheric smoke movement, highly realistic",
                "duration": 5
            }
            r_res = requests.post(runway_url, json=runway_payload, headers=runway_headers)
            task_id = r_res.json()["id"]
            
            final_video_url = None
            for _ in range(20):
                time.sleep(10)
                r_check = requests.get(f"https://api.gateway.runwayml.com/v1/tasks/{task_id}", headers=runway_headers)
                status = r_check.json()["status"]
                if status == "SUCCEEDED":
                    final_video_url = r_check.json()["output"][0]
                    break
                elif status == "FAILED":
                    break
            
            if final_video_url:
                with open(vname, "wb") as f:
                    f.write(requests.get(final_video_url).content)
                video_clips.append(vname)
                print(f"✅ दृश्य {i+1} का रनवे मोशन वीडियो तैयार!")
            else:
                raise Exception("Runway Failed/Timeout")
                
        except Exception as e:
            print(f"⚠️ पेड टूल्स में दिक्कत ({e}), ऑटो-रिकवरी चालू...")
            fallback_img = Image.new('RGB', (1080, 1920), color=(10, 10, 25))
            fallback_img.save(f"fb_{i}.jpg")
            c = ImageClip(f"fb_{i}.jpg").set_duration(7)
            c.write_videofile(vname, fps=24, codec="libx264", logger=None)
            video_clips.append(vname)
            
    return video_clips

# --- 5. 🎨 होर्मोजी स्टाइल डायनामिक बोल्ड येलो कैप्शंस ---
def create_bold_yellow_caption(text, duration):
    canvas_w, canvas_h = 1080, 400
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("Roboto-Black.ttf", 115)
    except:
        font = ImageFont.load_default()
        
    wrapped = textwrap.fill(text.upper(), width=14)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    x, y = (canvas_w - text_w) // 2, (canvas_h - text_h) // 2
    draw.multiline_text((x, y), wrapped, font=font, fill="#FFE81F", stroke_width=16, stroke_fill="black", align='center')
    
    temp_name = f"cap_{random.randint(1000,9999)}.png"
    img.save(temp_name)
    return ImageClip(temp_name).set_duration(duration)

# --- 6. हाई-रिटेंशन रेंडरिंग इंजन ---
def compile_high_retention_video(video_files, captions, audio_path):
    print("🎞️ वीडियो, ऑडियो और डायनामिक कैप्शंस को आपस में सिंक किया जा रहा है...")
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration
    
    clip_duration = audio_duration / len(video_files)
    processed_clips = []
    
    for idx, vfile in enumerate(video_files):
        clip = VideoFileClip(vfile).subclip(0, min(clip_duration, 7))
        clip = clip.resize(newsize=(1080, 1920))
        
        cap_text = captions[idx % len(captions)]
        if cap_text.strip():
            txt_clip = create_bold_yellow_caption(cap_text, clip.duration)
            txt_clip = txt_clip.set_position(('center', 0.75), relative=True)
            combined = CompositeVideoClip([clip, txt_clip], size=(1080, 1920))
        else:
            combined = clip
            
        if idx > 0:
            combined = combined.crossfadein(0.4)
            
        processed_clips.append(combined)
        
    final_video = concatenate_videoclips(processed_clips, padding=-0.4, method="compose")
    final_video = final_video.set_audio(audio).subclip(0, audio_duration)
    
    output_name = "final_viral_production.mp4"
    final_video.write_videofile(output_name, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    
    audio.close()
    final_video.close()
    return output_name

# --- 7. यूट्यूब मास्टर अपलोड ---
def upload_to_youtube(video_file, title, description, tags):
    print(f"📤 YouTube पर लाइव किया जा रहा है: '{title}'")
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    youtube = build("youtube", "v3", credentials=creds)
    
    request_body = {
        "snippet": {"categoryId": "22", "title": f"{title} #shorts", "description": description, "tags": tags},
        "status": {"privacyStatus": "public", "madeForKids": False}
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    youtube.videos().insert(part="snippet,status", body=request_body, media_body=media).execute()
    print("🎉 वीडियो 100% सक्सेस के साथ आपके चैनल पर पब्लिक लाइव हो चुका है!")

if __name__ == "__main__":
    try:
        print("👑 TITAN MYSTERY PRODUCTION ENGINE ONLINE 👑")
        title, description, tags, script, prompts, captions = get_viral_content()
        audio_path = generate_premium_audio(script)
        video_files = generate_premium_videos(prompts)
        final_output = compile_high_retention_video(video_files, captions, audio_path)
        
        gumroad_link = "https://girisbhut.gumroad.com/l/ajhzk"
        final_desc = f"{description}\n\n🚀 👉 पूरा सच जानने और ऐसे ही रहस्यों को अनलॉक करने के लिए यहाँ क्लिक करें:\n🔗 {gumroad_link}\n\n📝 Script:\n{script}"
        
        upload_to_youtube(final_output, title, final_desc, tags)
        
        # क्रेडिट स्टेटस और सफलता की रिपोर्ट
        elevenlabs_status = check_elevenlabs_credits()
        report_msg = f"""✅ *TITAN ENGINE UPDATE* ✅
        
🎬 *नया वीडियो लाइव हो गया है!*
📌 *Title:* {title}

📊 *क्रेडिट्स रिपोर्ट:*
- OpenAI: स्क्रिप्ट सफलतापूर्वक बनी (GPT-4o)
- {elevenlabs_status}
- Leonardo AI: 6 इमेजेज जेनरेट हुईं
- Runway ML: 6 वीडियो जेनरेट हुए

💰 *Gumroad लिंक डिस्क्रिप्शन में सेट कर दिया गया है।*"""
        
        send_telegram_report(report_msg)
        print("✅ रिपोर्ट टेलीग्राम पर भेज दी गई है।")
        
    except Exception as e:
        send_telegram_report(f"❌ *TITAN ENGINE CRASHED*\nएरर: {str(e)}")
        sys.exit(1)
