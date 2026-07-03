import os
import sys
import requests
import urllib.parse
import time
import random
from openai import OpenAI
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# 🛠️ PIL बग फिक्स (वीडियो एडिटर को क्रैश होने से बचाने के लिए)
if not hasattr(Image, 'Resampling'):
    Image.Resampling = getattr(Image, 'LANCZOS', 1)
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# --- 1. प्रीमियम API चाबियां ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, OPENAI_KEY, ELEVEN_KEY]):
    print("❌ एरर: कोई ज़रूरी API Key या Token गायब है! GitHub Secrets चेक करें।")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_KEY)

# --- 2. OpenAI से डार्क मिस्ट्री स्क्रिप्ट और 4 इमेजेस की मांग ---
def get_mystery_script():
    print("🧠 OpenAI से रहस्यमयी स्क्रिप्ट सोची जा रही है...")
    prompt = """
    Write a 40-second YouTube Short script about a terrifying, unsolved mystery or dark space anomaly in Hindi.
    Format EXACTLY like this (No extra text):
    TITLE: [Catchy Viral English Title]
    PROMPT1: [Dark creepy highly detailed image prompt 1]
    PROMPT2: [Dark creepy highly detailed image prompt 2]
    PROMPT3: [Dark creepy highly detailed image prompt 3]
    PROMPT4: [Dark creepy highly detailed image prompt 4]
    SCRIPT: [Hindi voiceover script. Must have a strong 3-second hook. End with asking to subscribe]
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=400
        )
        text = response.choices[0].message.content
        
        title = text.split("TITLE:")[1].split("PROMPT1:")[0].strip()
        p1 = text.split("PROMPT1:")[1].split("PROMPT2:")[0].strip()
        p2 = text.split("PROMPT2:")[1].split("PROMPT3:")[0].strip()
        p3 = text.split("PROMPT3:")[1].split("PROMPT4:")[0].strip()
        p4 = text.split("PROMPT4:")[1].split("SCRIPT:")[0].strip()
        script = text.split("SCRIPT:")[1].strip().replace("*", "")
        
        print(f"✅ स्क्रिप्ट और प्रॉम्प्ट तैयार: {title}")
        return title, script, [p1, p2, p3, p4]
    except Exception as e:
        print(f"❌ OpenAI एरर: {e}")
        sys.exit(1)

# --- 3. ElevenLabs से सस्पेंस वाली आवाज़ (Rachel Voice) ---
def generate_audio(script):
    print("🎙️ ElevenLabs से प्रीमियम सस्पेंस आवाज़ बन रही है...")
    voice_id = "21m00Tcm4TlvDq8ikWAM" 
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    data = {"text": script, "model_id": "eleven_multilingual_v2"}
    
    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 200:
        print(f"❌ ElevenLabs एरर: {response.text}")
        sys.exit(1)
        
    audio_path = "voice.mp3"
    with open(audio_path, "wb") as f:
        f.write(response.content)
    print("✅ ऑडियो फाइल बन गई!")
    return audio_path

# --- 4. AI इमेजेस बनाना (Robust Retry System के साथ) ---
def generate_and_format_images(prompts):
    print("🎨 AI से डार्क इमेजेस जनरेट हो रही हैं...")
    image_files = []
    style = ", cinematic lighting, 8k, photorealistic, dark mystery vibe, no text"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for i, p in enumerate(prompts):
        fname = f"scene_{i}.jpg"
        success = False
        
        # 3 बार कोशिश करने वाला लूप (ताकि खराब फाइल आए तो क्रैश न हो)
        for attempt in range(3):
            try:
                seed = random.randint(1000, 99999) # हर बार नई तस्वीर के लिए
                url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p + style)}?width=1080&height=1920&nologo=true&seed={seed}"
                
                print(f"तस्वीर {i+1} डाउनलोड हो रही है (कोशिश {attempt+1})...")
                res = requests.get(url, headers=headers, timeout=30)
                
                # चेक करें कि फाइल सही से आई है और खाली नहीं है
                if res.status_code == 200 and len(res.content) > 1000:
                    with open(fname, "wb") as f:
                        f.write(res.content)
                    
                    # इमेज को यूट्यूब शॉर्ट्स के साइज में काटना
                    img = Image.open(fname).convert("RGB")
                    target_ratio = 1080 / 1920
                    img_ratio = img.width / img.height
                    if img_ratio > target_ratio:
                        new_width = int(img.height * target_ratio)
                        left = (img.width - new_width) / 2
                        img = img.crop((left, 0, left + new_width, img.height))
                    else:
                        new_height = int(img.width / target_ratio)
                        top = (img.height - new_height) / 2
                        img = img.crop((0, top, img.width, top + new_height))
                        
                    img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
                    img.save(fname)
                    image_files.append(fname)
                    success = True
                    break # सफलता मिली तो लूप से बाहर आ जाएं
            except Exception as e:
                print(f"⚠️ तस्वीर {i+1} में एरर: {e}, फिर से कोशिश कर रहे हैं...")
                time.sleep(3)
                
        if not success:
            print(f"❌ एरर: तस्वीर {i+1} 3 बार में भी नहीं बन पाई।")
            sys.exit(1)
            
    print("✅ इमेजेस तैयार हो गईं!")
    return image_files

# --- 5. वीडियो एडिटिंग (मोशन और ज़ूम के साथ) ---
def create_video(audio_path, image_files):
    print("🎬 वीडियो रेंडर हो रहा है (मोशन इफ़ेक्ट के साथ)...")
    audio = AudioFileClip(audio_path)
    img_duration = audio.duration / len(image_files) 
    
    clips = []
    for img in image_files:
        clip = ImageClip(img).set_duration(img_duration)
        clip = clip.resize(lambda t: 1 + 0.05 * t).set_position(('center', 'center'))
        clips.append(clip)
        
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.set_audio(audio)
    
    output_file = "final_mystery_short.mp4"
    final_video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    
    audio.close()
    final_video.close()
    print("✅ असली MP4 वीडियो 100% रेडी है!")
    return output_file

# --- 6. YouTube पर अपलोड ---
def upload_to_youtube(video_file, title, description):
    print(f"📤 YouTube पर '{title}' अपलोड हो रहा है...")
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    youtube = build("youtube", "v3", credentials=creds)
    
    request_body = {
        "snippet": {
            "categoryId": "22",
            "title": f"{title} #shorts",
            "description": description,
            "tags": ["shorts", "mystery", "unsolved", "creepy", "viral", "facts"]
        },
        "status": {
            "privacyStatus": "public", 
            "madeForKids": False
        }
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    response = request.execute()
    print(f"🎉 बधाई हो! वायरल मिस्ट्री वीडियो लाइव है: https://www.youtube.com/watch?v={response['id']}")

if __name__ == "__main__":
    print("🚀 Mystery AI Engine स्टार्ट हो रहा है...")
    title, script, prompts = get_mystery_script()
    audio_path = generate_audio(script)
    images = generate_and_format_images(prompts)
    final_video = create_video(audio_path, images)
    
    description = f"{title}\n\nदुनिया और अंतरिक्ष के सबसे खूंखार रहस्य! 🌌✨ #shorts #mystery #viral #creepy\n\n📝 Script:\n{script}"
    upload_to_youtube(final_video, title, description)
    print("✅ आज का काम पूरा हुआ! मशीन कल इसी समय अपने आप चालू होगी।")
