import os
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# गिटहब सीक्रेट्स से चाबियां लोड करना
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("❌ एरर: YouTube की चाबियां नहीं मिलीं! कृपया GitHub Secrets चेक करें।")
    sys.exit(1)

def authenticate_youtube():
    print("🔄 YouTube में लॉगिन हो रहा है...")
    try:
        creds = Credentials(
            token=None,
            refresh_token=REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
        youtube = build("youtube", "v3", credentials=creds)
        print("✅ YouTube ऑथेंटिकेशन सफल!")
        return youtube
    except Exception as e:
        print(f"❌ YouTube लॉगिन फेल: {e}")
        sys.exit(1)

def generate_content():
    print("🧠 AI से कंटेंट बनाना शुरू (OpenAI, ElevenLabs, Leonardo, Runway)...")
    video_file = "final_video.mp4"
    if not os.path.exists(video_file):
        with open(video_file, 'wb') as f:
            f.write(b"dummy video content")
    return video_file, "Mystic Universe - AI Generated Video", "यह वीडियो AI द्वारा बनाया गया है।"

def upload_to_youtube(youtube, video_file, title, description):
    print(f"📤 '{title}' को YouTube पर अपलोड किया जा रहा है...")
    try:
        request_body = {
            "snippet": {
                "categoryId": "22",
                "title": title,
                "description": description,
                "tags": ["AI", "Mystic", "Shorts"]
            },
            "status": {
                "privacyStatus": "private",
                "madeForKids": False
            }
        }
        media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        )
        response = request.execute()
        print(f"🎉 बधाई हो! वीडियो सफलतापूर्वक अपलोड हो गया: https://www.youtube.com/watch?v={response['id']}")
    except Exception as e:
        print(f"❌ अपलोड में गड़बड़ हुई: {e}")

if __name__ == "__main__":
    print("🚀 Mystic AI Bot स्टार्ट हो रहा है...")
    yt_service = authenticate_youtube()
    video_path, vid_title, vid_desc = generate_content()
    upload_to_youtube(yt_service, video_path, vid_title, vid_desc)
    print("✅ सारा काम खत्म! मशीन बंद हो रही है।")
