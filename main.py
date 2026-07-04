import os
import sys
import requests
import time
import random
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

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, OPENAI_KEY, ELEVEN_KEY, LEONARDO_KEY, RUNWAY_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ एरर: कोई प्रीमियम चाबी या टेलीग्राम टोकन गायब है! कृपया GitHub Secrets चेक करें।")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_KEY)

# --- 2. रिपोर्टिंग और क्रेडिट चेक फंक्शन्स ---
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
            used = data['character_count']
            total = data['character_limit']
            remain = total - used
            return f"<b>ElevenLabs:</b> {remain} कैरेक्टर्स बाकी हैं (कुल: {total})"
        return "<b>ElevenLabs:</b> क्रेडिट डेटा अनुपलब्ध"
    except:
        return "<b>ElevenLabs:</b> क्रेडिट चेक विफल"

def check_leonardo_credits():
    try:
        url = "https://cloud.leonardo.ai/api/rest/v1/me"
        headers = {"accept": "application/json", "authorization": f"Bearer {LEONARDO_KEY}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            details = res.json()
            remain = details.get('user_details', [{}])[0].get('api_credit_volume', 'N/A')
            return f"<b>Leonardo AI:</b> {remain} टोकन्स बाकी हैं"
        return "<b>Leonardo AI:</b> क्रेडिट डेटा अनुपलब्ध"
    except:
        return "<b>Leonardo AI:</b> क्रेडिट चेक विफल"

def check_runway_credits():
    """Runway ML का क्रेडिट चेक सिस्टम"""
    try:
        # Runway के नए API में डायरेक्ट क्रेडिट एंडपॉइंट सीमित हो सकता है, लेकिन हम इसे सुरक्षित तरीके से कॉल करेंगे।
        url = "https://api.gateway.runwayml.com/v1/account"
        headers = {"Authorization": f"Bearer {RUNWAY_KEY}", "X-Runway-Version": "2024-11-06"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            # भविष्य में अगर Runway API में 'credits' फील्ड आता है, तो यह उसे पकड़ लेगा
            data = res.json()
            remain = data.get('credits', 'डैशबोर्ड में चेक करें (API में सीधा सपोर्ट नहीं)')
            return f"<b>Runway ML:</b> {remain}"
        return "<b>Runway ML:</b> API से सीधे क्रेडिट दिखाने की अनुमति नहीं (डैशबोर्ड देखें)"
    except:
        return "<b>Runway ML:</b> क्रेडिट चेक विफल"

# --- 3. सुपर वायरल, अनसुनी कहानी जनरेशन (GPT-4o) ---
def get_viral_content():
    print("🧠 GPT-4o से 50-सेकंड की एकदम अनसुनी और ज्ञानवर्धक स्क्रिप्ट लिखी जा रही है...")
    master_prompt = """
    Write an ULTRA-VIRAL, high-retention 45-50 second YouTube Short script about a RARE, UNHEARD-OF (Ansuni) and mind-blowing space or historical mystery in Hindi.
    
    STRICT RULES FOR VIRALITY, STORYTELLING & KNOWLEDGE:
    1. NO FLUFF, PURE VALUE: Do not use generic, boring, or overused facts. The mystery must be factually accurate, highly obscure, and actively increase the viewer's knowledge. No nonsense or filler words.
    2. HOOK: The first 3 seconds MUST be a brutal pattern interrupt. Start exactly with a shocking hook that forces them to stop scrolling. 
    3. PACING & STORY: Write exactly 110-120 words in Hindi for a solid 45-50 second suspenseful delivery. Keep them hooked with a unique narrative arc (Hook -> Deep Mystery/Knowledge -> Mind-blowing conclusion).
    4. CTA: The very last sentence must be exactly: "पूरा सच जानने और ऐसे ही रहस्यों को अनलॉक करने के लिए, डिस्क्रिप्शन में दिए गए लिंक पर क्लिक करें।"
    5. PROMPTS: Provide 6 ultra-realistic image prompts. Use keywords like "hyper-realistic, 8k resolution, cinematic lighting, unreal engine 5, terrifying atmospheric depth, highly detailed".
    6. CAPTIONS: Provide 6 short, punchy 2-3 word phrases for on-screen captions matching the narrative arc.
    
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
            temperature=0.85 # थोडा सा क्रिएटिविटी बढाया ताकि एकदम अनोखी कहानियाँ मिलें
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

# --- 4. प्रीमियम वॉयसओवर ---
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

# --- 5. हॉलीवुड-ग्रेड विजुअल्स (Leonardo + Runway) ---
def generate_premium_videos(prompts):
    video_clips = []
    leo_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    leo_headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Bearer {LEONARDO_KEY}"}
    
    runway_url = "https://api.gateway.runwayml.com/v1/image_to_video"
    runway_headers = {"Authorization": f"Bearer {RUNWAY_KEY}", "X-Runway-Version": "2024-11-06", "Content-Type": "application/json"}
    
    for i, p in enumerate(prompts):
        vname = f"clip_{i}.mp4"
        print(f"\n🎨 [लियोनार्डो] दृश्य {i+1} तैयार हो रहा है...")
        
        try:
            payload = {"height": 1024, "width": 576, "modelId": "5c232e9a-9061-4be1-90ca-94d856b152e8", "prompt": p + ", masterpiece, hyper-realistic, dark cinematic lighting, 8k", "num_images": 1}
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

            print(f"🎬 [रनवे एमएल] मोशन वीडियो बन रहा है...")
            runway_payload = {
                "model": "gen3a_turbo",
                "promptImage": img_url,
                "promptText": "slow cinematic camera zoom in, eerie atmospheric smoke movement, highly realistic, volumetric lighting",
                "duration": 5
            }
            r_res = requests.post(runway_url, json=runway_payload, headers=runway_headers)
            task_id = r_res.json()["id"]
            
            final_video_url = None
            for _ in range(25):
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
            else:
                raise Exception("Runway Failed/Timeout")
                
        except Exception as e:
            print(f"⚠️ दृश्य {i+1} में दिक्कत ({e}), फ़ॉलबैक इस्तेमाल कर रहे हैं...")
            fallback_img = Image.new('RGB', (1080, 1920), color=(15, 15, 25))
            fallback_img.save(f"fb_{i}.jpg")
            c = ImageClip(f"fb_{i}.jpg").set_duration(6)
            c.write_videofile(vname, fps=24, codec="libx264", logger=None)
            video_clips.append(vname)
            
    return video_clips

# --- 6. डायनामिक बोल्ड कैप्शंस ---
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

# --- 7. रेंडरिंग इंजन ---
def compile_high_retention_video(video_files, captions, audio_path):
    print("🎞️ वीडियो रेंडर किया जा रहा है...")
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
            combined = combined.crossfadein(0.5)
            
        processed_clips.append(combined)
        
    final_video = concatenate_videoclips(processed_clips, padding=-0.5, method="compose")
    final_video = final_video.set_audio(audio).subclip(0, audio_duration)
    
    output_name = "final_viral_production.mp4"
    final_video.write_videofile(output_name, fps=30, codec="libx264", audio_codec="aac", preset="fast", logger=None)
    
    audio.close()
    final_video.close()
    return output_name

# --- 8. यूट्यूब अपलोड और लिंक जेनरेशन ---
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
        print("👑 TITAN VIRAL PRODUCTION ENGINE ONLINE 👑")
        
        # 1. कंटेंट जनरेट करें
        title, description, tags, script, prompts, captions, gpt_tokens = get_viral_content()
        audio_path = generate_premium_audio(script)
        video_files = generate_premium_videos(prompts)
        final_output = compile_high_retention_video(video_files, captions, audio_path)
        
        # 2. अपलोड करें
        gumroad_link = "https://girisbhut.gumroad.com/l/ajhzk"
        final_desc = f"{description}\n\n🚀 👉 पूरा सच जानने और ऐसे ही रहस्यों को अनलॉक करने के लिए यहाँ क्लिक करें:\n🔗 {gumroad_link}\n\n📝 Script:\n{script}"
        video_url = upload_to_youtube(final_output, title, final_desc, tags)
        
        # 3. प्रीमियम API क्रेडिट चेक
        elevenlabs_status = check_elevenlabs_credits()
        leonardo_status = check_leonardo_credits()
        runway_status = check_runway_credits()
        
        # 4. टेलीग्राम पर संपूर्ण रिपोर्ट
        report_msg = f"""✅ <b>वायरल वीडियो सफलतापूर्वक अपलोड हो गया!</b> ✅
        
🎬 <b>Title:</b> {title}
🔗 <b>YouTube Link:</b> <a href='{video_url}'>यहाँ क्लिक करके देखें</a>

📊 <b>प्रीमियम API क्रेडिट रिपोर्ट:</b>
- <b>OpenAI (GPT-4o):</b> उपयोग किए गए टोकन: {gpt_tokens}
- {elevenlabs_status}
- {leonardo_status}
- {runway_status}

💰 Gumroad लिंक डिस्क्रिप्शन में एक्टिव है। अगले 30 दिन का मोनेटाइजेशन प्लान ट्रैक पर है!"""
        
        send_telegram_report(report_msg)
        print("✅ रिपोर्ट टेलीग्राम पर भेज दी गई है।")
        
    except Exception as e:
        error_msg = f"❌ <b>इंजन क्रैश हो गया:</b>\nएरर: {str(e)}"
        send_telegram_report(error_msg)
        sys.exit(1)
