import os
import time
import requests
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from backend.model import analyse_message, load_models

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

YOUTUBE_API = os.getenv("YOUTUBE_API_KEY")
API_URL = "http://127.0.0.1:8080/fetch_chat"
send_URL = "http://127.0.0.1:8080/set_stream"

SAVE_FILE = 'chat_data.csv'
POLL_INTERVAL_SECONDS = 10

# This is the file we write to, so the dashboard knows which CSV to read
CONFIG_FILE = "current_stream.txt"

youtube_service = None
live_chat_id = None
next_page_token = None




def initialize_youtube():
    global youtube_service
    try:
        youtube_service = build('youtube', 'v3', developerKey=YOUTUBE_API)
        print("✅ YouTube API initialized.")
        return True
    except Exception as e:
        print(f"❌ Error initializing YouTube API: {e}")
        print("❌ PLEASE CHECK your YOUTUBE_API_KEY in the .env file.")
        return False


def get_live_chat_id(video_id):
    global live_chat_id
    try:
        request = youtube_service.videos().list( # type: ignore
            part="liveStreamingDetails",
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
            print(f"❌ Error: Video with ID '{video_id}' not found.")
            return False

        live_details = response['items'][0].get('liveStreamingDetails')
        if not live_details:
            print(f"❌ Error: This video ('{video_id}') is not a live stream or is over.")
            return False

        live_chat_id = live_details.get('activeLiveChatId')
        if not live_chat_id:
            print(f"❌ Error: Could not find active live chat ID. Is the stream live right now?")
            return False

        print(f"✅ Live Chat ID found: {live_chat_id}")
        return live_chat_id

    except HttpError as e:
        print(f"❌ HTTP Error finding chat ID: {e}")
        if "keyInvalid" in str(e):
            print("❌ Your YOUTUBE_API_KEY is invalid or restricted.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def get_chat_poll(live_chat_id):
    global next_page_token
    try:
        request = youtube_service.liveChatMessages().list( # type: ignore
            liveChatId=live_chat_id,
            part="snippet,authorDetails",
            pageToken=next_page_token
        )
        response = request.execute()

        new_messages = response.get('items', [])
        next_page_token = response.get('nextPageToken', None)
        wait_time_ms = response.get('pollingIntervalMillis', 10000)
        last_poll_time = wait_time_ms / 1000.0 # Convert to seconds
        # ---

        if not new_messages:
            print("ℹ️ No new messages yet.")
            return wait_time_ms / 1000.0 # <--- THE FIX! (Returns a number)

        print(f"💬 Found {len(new_messages)} new messages...")
        for msg in new_messages:
            
            message_text = msg['snippet'].get('displayMessage')
            if not message_text:
                continue # Skip superchats/stickers
                
            author = msg['authorDetails']['displayName']
            
            # --- FIX 2: Added the missing 'timestamp' variable ---
            timestamp = msg['snippet']['publishedAt']
            
            print(f"[{timestamp}] {author}: {message_text}")

            try:
                # Use the correct variable names
                requests.post(API_URL, json={"user": author, "text": message_text})
            except Exception as e:
                print(f"⚠️ Failed to send message to API: {e}")

        return wait_time_ms / 1000.0 # Return the wait time

    except HttpError as e:
        print(f"❌ Error fetching chat: {e}")
        if "liveChatNotFound" in str(e):
            print("--- CHAT ENDED ---")
            raise SystemExit() # Stop the script
        if "quotaExceeded" in str(e):
            print("🔥 QUOTA EXCEEDED! Waiting for 60 seconds...")
            return 60.0
        return 10.0 # Default wait on error
    
    except Exception as e:
        print(f"❌ Unexpected Error in chat poll: {e}")
        return 10.0



def main():
    video_url = input("Enter YouTube live URL: ")

    if "v=" in video_url:
        video_id = video_url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in video_url:
        video_id = video_url.split("youtu.be/")[1].split("?")[0]
    else:
        print("❌ Invalid YouTube URL format.")
        return
    

    try:
        print(f"➡️  Telling server about new stream: {video_id}...")
        res = requests.post(send_URL, json={"url": video_url})
        
        if res.status_code == 200:
            data = res.json()
            new_filename = data.get("file") # Get the new CSV name from the server
            
            if not new_filename:
                print(f"❌ Server error: {data.get('error', 'Unknown error')}")
                return
                
            print(f"✅ Backend set to save data to: {new_filename}")


            # This is the "pointer" file for the dashboard
            with open(CONFIG_FILE, "w") as f:
                f.write(new_filename)
            print(f"✅ Wrote filename to {CONFIG_FILE} for dashboard.")
            
        else:
            print(f"⚠️ Could not set new stream in backend: {res.text}")
            return
    except Exception as e:
        print(f"⚠️ Failed to connect to backend API: {e}")
        print(" Is your 'chat.py' running in Terminal 1?")
        return
    
    if not initialize_youtube():
        return

    live_chat_id = get_live_chat_id(video_id)
    if not live_chat_id:
        return

    print("🔄 Fetching messages every 10 seconds... Press Ctrl+C to stop.")
    while True:
        # get_chat_poll will get messages AND return the new wait time
        wait_time = get_chat_poll(live_chat_id)
        
        # --- FIX 3: Removed the "double sleep" ---
        print(f"   (Waiting for {wait_time:.1f} seconds before next poll...)")
        time.sleep(wait_time) # type: ignore

if __name__ == "__main__":
    main()
