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
LEONARDO_KEY = os.environ.get("LEONARDO_API_KEY")

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
    print("🧠 GPT-4o से एकदम हाई-क्वालिटी वायरल स्क्रिप्ट लिखी जा रही है...")
    master_prompt = """
    Write a HYPER-VIRAL, high-retention 45-50 second YouTube Short script about a RARE, highly obscure historical or space mystery in Hindi.
    
    CRITICAL RULES:
    1. AVOID CLICHÉS: DO NOT use generic phrases like "वैज्ञानिक भी हैरान हैं" or "बिना मशीनों के कैसे बना". Provide SPECIFIC, deep, and mind-blowing facts.
    2. HOOK: First 3 seconds MUST be a direct, shocking question or brutal pattern interrupt.
    3. PACING: Exactly 110-120 words in Hindi for a fast-paced delivery.
    4. CTA: Only say "ऐसे ही रहस्यों के लिए सब्सक्राइब करें।" Do NOT ask them to check the description.
    5. PROMPTS: Provide 6 ultra-detailed Midjourney-v6 style image prompts. Keywords: "masterpiece, hyper-realistic, highly detailed, dark cinematic lighting, 8k resolution, unreal engine 5 render".
    6. CAPTIONS: Provide 6 short, punchy 2-3 word phrases for on-screen text.
    
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

# --- 5. हॉलीवुड-ग्रेड विजुअल्स (Leonardo Motion SVD AI) ---
def generate_premium_videos(prompts):
    video_clips = []
    leo_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    # ✅ बिल्कुल सही और टेस्टेड मोशन API
    motion_url = "https://cloud.leonardo.ai/api/rest/v1/generations-motion-svd"
    leo_headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Bearer {LEONARDO_KEY}"}
    
    for i, p in enumerate(prompts):
        vname = f"clip_{i}.mp4" 
        
        # 🟢 स्टेप 1: पहले एक हाई-क्वालिटी 8K सिनेमैटिक बेस इमेज बनाना
        print(f"\n🎨 [लियोनार्डो] दृश्य {i+1} की 8K बेस इमेज बन रही है...")
        payload = {
            "height": 1024, 
            "width": 512, 
            "prompt": p, 
            "num_images": 1
        }
        res = requests.post(leo_url, json=payload, headers=leo_headers)
        if res.status_code != 200:
            raise Exception(f"Leonardo Image API एरर: {res.text}")
            
        gen_id = res.json()["sdGenerationJob"]["generationId"]
        
        img_id = None
        for _ in range(20): 
            time.sleep(6)
            check = requests.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}", headers=leo_headers)
            status = check.json()["generations_by_pk"]["status"]
            if status == "COMPLETE":
                img_id = check.json()["generations_by_pk"]["generated_images"][0]["id"]
                break
            elif status == "FAILED":
                raise Exception("Leonardo बेस इमेज फेल हो गई।")
                
        if not img_id:
            raise Exception("Leonardo टाइमआउट - इमेज नहीं बनी")

        # 🟢 स्टेप 2: उस इमेज को असली हाई-क्वालिटी वीडियो में बदलना (Leonardo Motion SVD)
        print(f"🎬 [लियोनार्डो मोशन] इमेज में जान डाली जा रही है (Motion SVD Video)...")
        m_payload = {
            "imageId": img_id, 
            "motionStrength": 5,
            "isPublic": False,
            "isInitImage": False
        }
        m_res = requests.post(motion_url, json=m_payload, headers=leo_headers)
        if m_res.status_code != 200:
            raise Exception(f"Leonardo Motion SVD API एरर: {m_res.text}")
            
        m_gen_id = m_res.json().get("motionSvdGenerationJob", {}).get("generationId")
        if not m_gen_id:
            raise Exception(f"Leonardo Motion SVD ID नहीं मिला: {m_res.text}")
        
        vid_url = None
        for _ in range(40): 
            time.sleep(10)
            m_check = requests.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{m_gen_id}", headers=leo_headers)
            m_status = m_check.json()["generations_by_pk"]["status"]
            if m_status == "COMPLETE":
                gen_imgs = m_check.json()["generations_by_pk"]["generated_images"][0]
                vid_url = gen_imgs.get("motionMP4URL")
                break
            elif m_status == "FAILED":
                raise Exception("Leonardo Motion वीडियो फेल हो गया।")
                
        if not vid_url:
            raise Exception("Leonardo Motion टाइमआउट - वीडियो रेंडर नहीं हुआ या MP4 URL नहीं मिला।")

        # 🟢 स्टेप 3: असली .mp4 वीडियो डाउनलोड करना
        print(f"📥 असली मोशन वीडियो डाउनलोड किया जा रहा है...")
        vid_res = requests.get(vid_url, stream=True)
        if vid_res.status_code == 200:
            with open(vname, "wb") as f:
                for chunk in vid_res.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            
            video_clips.append(vname)
            print(f"✅ लियोनार्डो मोशन वीडियो {i+1} सफलता से सेव हो गया!")
        else:
            raise Exception(f"Leonardo वीडियो फाइल डाउनलोड फेल (Status: {vid_res.status_code})")
            
    return video_clips

# --- 6. डायनामिक बोल्ड कैप्शंस (✅ 100% बुलेटप्रूफ फॉन्ट डाउनलोडर) ---
def create_bold_yellow_caption(text, duration):
    canvas_w, canvas_h = 1080, 400
    img = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_path = "Roboto-Black.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://raw.githubusercontent.com/google/fonts/main/apache/roboto/Roboto-Black.ttf"
            urllib.request.urlretrieve(url, font_path)
        except:
            pass
    
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

# --- 7. हाई-रिटेंशन रेंडरिंग (Real Video Compiler) ---
def compile_high_retention_video(video_files, captions, audio_path):
    print("🎞️ असली मोशन वीडियो रेंडर किया जा रहा है...")
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration
    
    clip_duration = audio_duration / len(video_files)
    processed_clips = []
    source_clips_to_close = [] 
    
    for idx, vfile in enumerate(video_files):
        # अब यह वापस असली वीडियो क्लिप है
        base_clip = VideoFileClip(vfile)
        source_clips_to_close.append(base_clip)
        
        # वीडियो को ऑडियो के हिस्से के बराबर लूप करना
        looped_clip = base_clip.fx(loop, duration=clip_duration)
        final_looped = looped_clip.resize(newsize=(1080, 1920))
        
        cap_text = captions[idx % len(captions)]
        if cap_text.strip():
            txt_clip = create_bold_yellow_caption(cap_text, final_looped.duration)
            txt_clip = txt_clip.set_position(('center', 0.75), relative=True)
            combined = CompositeVideoClip([final_looped, txt_clip], size=(1080, 1920))
        else:
            combined = final_looped
            
        if idx > 0:
            combined = combined.crossfadein(0.5)
            
        processed_clips.append(combined)
        
    final_video = concatenate_videoclips(processed_clips, padding=-0.5, method="compose")
    final_video = final_video.set_audio(audio).subclip(0, audio_duration)
    
    output_name = "final_viral_production.mp4"
    final_video.write_videofile(output_name, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4, logger=None)
    
    audio.close()
    final_video.close()
    for c in source_clips_to_close + processed_clips:
        try:
            c.close()
        except:
            pass
            
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
        print("👑 TITAN VIRAL PRODUCTION ENGINE ONLINE 👑")
        
        title, description, tags, script, prompts, captions, gpt_tokens = get_viral_content()
        audio_path = generate_premium_audio(script)
        video_files = generate_premium_videos(prompts) # असली मोशन वीडियो
        final_output = compile_high_retention_video(video_files, captions, audio_path)
        
        gumroad_link = "https://girisbhut.gumroad.com/l/ajhzk"
        final_desc = f"{description}\n\n🌟 और अधिक गहराई से जानने के लिए विजिट करें:\n🔗 {gumroad_link}"
        video_url = upload_to_youtube(final_output, title, final_desc, tags)
        
        elevenlabs_status = check_elevenlabs_credits()
        leonardo_status = check_leonardo_credits()
        ram_status = check_ram_usage()
        
        report_msg = f"""✅ <b>प्रीमियम वायरल वीडियो अपलोड हो गया!</b> ✅
        
🎬 <b>Title:</b> {title}
🔗 <b>YouTube Link:</b> <a href='{video_url}'>यहाँ क्लिक करके देखें</a>

📊 <b>सिस्टम और API स्टेटस:</b>
- {ram_status}
- {elevenlabs_status}
- {leonardo_status}
- टोकन उपयोग (GPT-4o): {gpt_tokens}
- क्वालिटी: 100% Real Leonardo Motion SVD Video
- अपलोड स्टेटस: सफलता"""
        
        send_telegram_report(report_msg)
        print("✅ रिपोर्ट टेलीग्राम पर भेज दी गई है।")
        
    except Exception as e:
        ram_crash_status = check_ram_usage()
        error_details = str(e)
        
        crash_msg = f"""🚨 <b>मशीन क्रैश हो गई (वीडियो अपलोड नहीं हुआ)</b> 🚨
        
❌ <b>समस्या (इसे ठीक करें):</b> 
{error_details}

💻 <b>क्रैश के समय सर्वर का स्टेटस:</b>
- {ram_crash_status}

(यह गड़बड़ी API या कोडिंग की हो सकती है। ऊपर दी गई समस्या को सीटीओ (मुझे) भेजें।)"""
        
        send_telegram_report(crash_msg)
        print(f"❌ इंजन क्रैश हो गया। डिटेल टेलीग्राम पर भेज दी गई है।")
        sys.exit(1)
