import os
import sys
import requests
from openai import OpenAI
from moviepy.editor import AudioFileClip, ColorClip
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 1. चाबियां सेट करना ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY")

if not OPENAI_KEY or not ELEVEN_KEY:
    print("❌ एरर: OpenAI या ElevenLabs की चाबी नहीं मिली!")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_KEY)

# --- 2. OpenAI से वायरल स्क्रिप्ट लेना ---
def get_viral_script():
    print("🧠 OpenAI से वायरल स्क्रिप्ट सोची जा रही है...")
    prompt = """
    Write a 30-second YouTube Short script about a mysterious space or mystic fact in Hindi. 
    Format EXACTLY like this (no extra text):
    TITLE: [Catchy Viral Title in English]
    SCRIPT: [Only the spoken words for the voiceover in Hindi. Must have a strong 3-second hook]
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        text = response.choices[0].message.content
        title = text.split("TITLE:")[1].split("SCRIPT:")[0].strip()
        script = text.split("SCRIPT:")[1].strip()
        print(f"✅ स्क्रिप्ट तैयार: {title}")
        return title, script
    except Exception as e:
        print(f"❌ OpenAI एरर: {e}")
        sys.exit(1)

# --- 3. ElevenLabs से असली आवाज़ बनाना ---
def generate_audio(script):
    print("🎙️ ElevenLabs से प्रीमियम आवाज़ बन रही है...")
    voice_id = "pNInz6obpgDQGcFmaJcg" # Adam voice
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    data = {"text": script, "model_id": "eleven_multilingual_v2"} # हिंदी के लिए v2 मॉडल
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            print(f"❌ ElevenLabs एरर: {response.text}")
            sys.exit(1)
            
        audio_path = "voice.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)
        print("✅ ऑडियो फाइल बन गई!")
        return audio_path
    except Exception as e:
        print(f"❌ ऑडियो जनरेशन फेल: {e}")
        sys.exit(1)

# --- 4. MoviePy से असली MP4 वीडियो तैयार करना ---
def create_final_short(audio_path):
    print("🎞️ असली चलने वाला MP4 वीडियो तैयार हो रहा है...")
    try:
        # ऑडियो लोड करें
        audio = AudioFileClip(audio_path)
        
        # 9:16 (1080x1920) का एक डार्क मिस्टिक (गहरा नीला/काला) बैकग्राउंड बनाएं
        bg_clip = ColorClip(size=(1080, 1920), color=(10, 10, 30))
        bg_clip = bg_clip.set_duration(audio.duration)
        
        # ऑडियो को वीडियो में सेट करें
        final_video = bg_clip.set_audio(audio)
        
        # असली MP4 फाइल बनाएं
        output_file = "final_viral_short.mp4"
        final_video.write_videofile(
            output_file,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=2,
            preset="ultrafast"
        )
        print("✅ असली MP4 वीडियो 100% रेडी है!")
        return output_file
    except Exception as e:
        print(f"❌ MP4 बनाने में एरर: {e}")
        sys.exit(1)

# --- 5. YouTube अपलोड ---
def upload_to_youtube(video_file, title, description):
    print(f"📤 YouTube पर '{title}' अपलोड हो रहा है...")
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    youtube = build("youtube", "v3", credentials=creds)
    
    request_body = {
        "snippet": {
            "categoryId": "22",
            "title": f"{title} #shorts",
            "description": description,
            "tags": ["shorts", "viral", "mystic", "space", "facts", "ai"]
        },
        "status": {
            "privacyStatus": "public", 
            "madeForKids": False
        }
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    response = request.execute()
    print(f"🎉 वायरल वीडियो लाइव है: https://www.youtube.com/watch?v={response['id']}")

if __name__ == "__main__":
    print("🚀 Mystic AI Bot - Phase 2 स्टार्ट हो रहा है...")
    title, script = get_viral_script()
    audio_path = generate_audio(script)
    final_video = create_final_short(audio_path)
    
    description = f"{title}\n\nरहस्यमयी अंतरिक्ष के फैक्ट्स! 🌌✨ #shorts #mystic #space #viral #aivideo"
    upload_to_youtube(final_video, title, description)
    print("✅ मशीन का काम पूरा हुआ!")
