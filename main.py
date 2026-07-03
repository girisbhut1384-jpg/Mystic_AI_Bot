import os
import sys
import requests
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
LEONARDO_KEY = os.environ.get("LEONARDO_API_KEY")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, OPENAI_KEY, ELEVEN_KEY, LEONARDO_KEY]):
    print("❌ एरर: कोई ज़रूरी API Key या Token गायब है! GitHub Secrets चेक करें।")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_KEY)

# --- 2. OpenAI से डार्क मिस्ट्री स्क्रिप्ट और प्रॉम्प्ट्स लेना ---
def get_mystery_script():
    print("🧠 OpenAI से रहस्यमयी स्क्रिप्ट सोची जा रही है...")
    prompt = """
    Write a 40-second YouTube Short script about a terrifying, unsolved mystery or dark space anomaly in Hindi.
    Format EXACTLY like this (No extra text):
    TITLE: [Catchy Viral English Title]
    PROMPT1: [Dark creepy highly detailed master cinematic image prompt 1]
    PROMPT2: [Dark creepy highly detailed master cinematic image prompt 2]
    PROMPT3: [Dark creepy highly detailed master cinematic image prompt 3]
    PROMPT4: [Dark creepy highly detailed master cinematic image prompt 4]
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

# --- 4. 👑 Leonardo AI से प्रीमियम इमेजेस जनरेट करना (Corrected API URL) ---
def generate_leonardo_images(prompts):
    print("🎨 Leonardo AI (Paid) से अल्ट्रा-एचडी तस्वीरें जनरेट हो रही हैं...")
    image_files = []
    
    # बिल्कुल सही और नया Leonardo API एड्रेस
    url_gen = "https://cloud.leonardo.ai/api/rest/v1/generations"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {LEONARDO_KEY}"
    }
    
    for i, p in enumerate(prompts):
        fname = f"scene_{i}.jpg"
        print(f"🎬 तस्वीर {i+1} का ऑर्डर लियोनार्डो को दिया जा रहा है...")
        
        payload = {
            "height": 1024, # लियोनार्डो का स्टैण्डर्ड वर्टीकल साइज़ (Fail-safe)
            "width": 576, 
            "prompt": p + ", dark mystical atmosphere, hyper-detailed, 8k resolution, cinematic lighting",
            "num_images": 1
        }
        
        try:
            res = requests.post(url_gen, json=payload, headers=headers)
            if res.status_code != 200:
                print(f"⚠️ लियोनार्डो ऑर्डर एरर: {res.text}")
                raise Exception("Leonardo API Refused")
                
            generation_id = res.json()["sdGenerationJob"]["generationId"]
            
            # पोलिंग लूप (इंतज़ार करना)
            url_check = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
            photo_url = None
            
            for check_attempt in range(15):
                time.sleep(10)
                print(f"⏳ तस्वीर {i+1} के बनने का इंतज़ार हो रहा है ({check_attempt*10}s)...")
                check_res = requests.get(url_check, headers=headers)
                
                if check_res.status_code == 200:
                    gen_data = check_res.json()["generations_by_pk"]
                    if gen_data["status"] == "COMPLETE":
                        photo_url = gen_data["generated_images"][0]["url"]
                        break
                    elif gen_data["status"] == "FAILED":
                        print("❌ लियोनार्डो सर्वर पर फोटो फेल हो गई।")
                        break
            
            if photo_url:
                img_data = requests.get(photo_url).content
                with open(fname, "wb") as f:
                    f.write(img_data)
                
                # इसे परफेक्ट यूट्यूब शॉर्ट्स (1080x1920) साइज में बड़ा (Upscale) करना
                img = Image.open(fname).convert("RGB")
                img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
                img.save(fname)
                
                image_files.append(fname)
                print(f"✅ तस्वीर {i+1} सफलतापूर्वक डाउनलोड हो गई!")
            else:
                raise Exception("Timeout or Failed status")
                
        except Exception as e:
            print(f"⚠️ लियोनार्डो में दिक्कत आई: {e}। सेफ्टी के लिए डार्क बैकग्राउंड इस्तेमाल कर रहे हैं...")
            fallback_img = Image.new('RGB', (1080, 1920), color=(10, 10, 25))
            fallback_img.save(fname)
            image_files.append(fname)
            
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
    images = generate_leonardo_images(prompts)
    final_video = create_video(audio_path, images)
    
    description = f"{title}\n\nदुनिया और अंतरिक्ष के सबसे खूंखार रहस्य! 🌌✨ #shorts #mystery #viral #creepy\n\n📝 Script:\n{script}"
    upload_to_youtube(final_video, title, description)
    print("✅ आज का काम पूरा हुआ! मशीन कल इसी समय अपने आप चालू होगी।")
