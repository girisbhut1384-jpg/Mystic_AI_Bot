import os
import sys
import time
import requests
from openai import OpenAI
from moviepy.editor import VideoFileClip, AudioFileClip
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 1. चाबियां सेट करना ---
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY")
LEO_KEY = os.environ.get("LEONARDO_API_KEY")
RUNWAY_KEY = os.environ.get("RUNWAYML_API_SECRET")

client = OpenAI(api_key=OPENAI_KEY)

# --- 2. OpenAI से वायरल स्क्रिप्ट और इमेज प्रॉम्प्ट लेना ---
def get_viral_script():
    print("🧠 OpenAI से वायरल स्क्रिप्ट सोची जा रही है...")
    prompt = """
    Write a 30-second YouTube Short script about a mysterious space or mystic fact. 
    Format EXACTLY like this (no extra text):
    TITLE: [Catchy Viral Title]
    PROMPT: [1 highly detailed image prompt for AI generation, dark mystic vibe, 9:16 aspect ratio]
    SCRIPT: [Only the spoken words for the voiceover. Must have a strong 3-second hook]
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", # अगर आपके पास gpt-4 का एक्सेस है, तो यहाँ gpt-4 लिख सकते हैं
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250
    )
    text = response.choices[0].message.content
    
    title = text.split("TITLE:")[1].split("PROMPT:")[0].strip()
    img_prompt = text.split("PROMPT:")[1].split("SCRIPT:")[0].strip()
    script = text.split("SCRIPT:")[1].strip()
    return title, img_prompt, script

# --- 3. ElevenLabs से सस्पेंस वाली आवाज़ बनाना ---
def generate_audio(script):
    print("🎙️ ElevenLabs से प्रीमियम आवाज़ बन रही है...")
    voice_id = "pNInz6obpgDQGcFmaJcg" # Adam voice (आप चाहें तो बदल सकते हैं)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    data = {"text": script, "model_id": "eleven_monolingual_v1"}
    
    response = requests.post(url, json=data, headers=headers)
    audio_path = "voice.mp3"
    with open(audio_path, "wb") as f:
        f.write(response.content)
    return audio_path

# --- 4. Leonardo AI से 9:16 हाई-क्वालिटी इमेज बनाना ---
def generate_image(prompt):
    print("🎨 Leonardo से 1080x1920 इमेज बन रही है...")
    # (यहाँ लियोनार्डो का असली API कोड आएगा। अभी टेस्टिंग के लिए हम एक डमी इमेज बना रहे हैं ताकि कोड न टूटे)
    # भविष्य के अपडेट में हम लियोनार्डो का पूरा पोलिंग (Polling) लूप यहाँ लगाएंगे
    time.sleep(2)
    return "dummy_image.jpg"

# --- 5. RunwayML से मोशन वीडियो बनाना ---
def generate_video(image_path):
    print("🎬 RunwayML से वीडियो में जान डाली जा रही है...")
    # (यहाँ रनवे का असली API कोड आएगा)
    time.sleep(2)
    return "dummy_video_no_audio.mp4"

# --- 6. MoviePy से ऑडियो और वीडियो को जोड़कर फाइनल शॉर्ट्स बनाना ---
def create_final_short(audio_path, video_path):
    print("🎞️ वीडियो और आवाज़ को जोड़कर फाइनल शॉर्ट तैयार हो रहा है...")
    try:
        # डमी क्रिएशन (जब असली फाइलें आ जाएंगी तब यह कोड उन्हें मर्ज करेगा)
        with open("final_viral_short.mp4", 'wb') as f:
            f.write(b"dummy video content")
        return "final_viral_short.mp4"
    except Exception as e:
        print(f"मर्जिंग में एरर: {e}")
        return "final_viral_short.mp4"

# --- 7. YouTube ऑथेंटिकेशन और अपलोड ---
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
            "privacyStatus": "public", # बॉस, अब यह सीधे PUBLIC अपलोड होगा!
            "madeForKids": False
        }
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    response = request.execute()
    print(f"🎉 वायरल वीडियो लाइव है: https://www.youtube.com/watch?v={response['id']}")

if __name__ == "__main__":
    print("🚀 Mystic AI वायरल मशीन स्टार्ट हो रही है...")
    try:
        title, img_prompt, script = get_viral_script()
        audio_path = generate_audio(script)
        image_path = generate_image(img_prompt)
        video_no_audio = generate_video(image_path)
        final_video = create_final_short(audio_path, video_no_audio)
        
        description = f"{title}\n\n#shorts #mystic #space #viral #aivideo"
        upload_to_youtube(final_video, title, description)
        
        print("✅ मिशन सक्सेसफुल! मिलते हैं 24 घंटे बाद।")
    except Exception as e:
        print(f"❌ मशीन में कोई गड़बड़ हुई: {e}")
