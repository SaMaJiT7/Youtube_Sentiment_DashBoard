from fastapi import FastAPI, BackgroundTasks # <-- FIX: Added BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import uvicorn
import os
import asyncio
import logging
import aiofiles
from contextlib import asynccontextmanager
from datetime import datetime

# --- Importing our main model ---
# <-- FIX 1: 'analyze_message' (with a 'z')
from backend.model import load_models, analyse_message

# <-- FIX 2: 'SAVE_FILE' (no 'S')
SAVE_FILE = "chat_data.csv" # The dashboard will read this file
BATCH_SAVE_SECONDS = 5.0    # Save data every 5 seconds
MAX_QUEUE_SIZE = 10000

# --- Setup (All your code here is perfect) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

message_queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)

async def batch_saver(queue: asyncio.Queue):
    """
    (Your batch_saver code is perfect, just uses SAVE_FILE)
    """
    global SAVE_FILE
    log.info("💾 Batch saver task started.")
    
    # Create 'data' folder if it doesn't exist
    os.makedirs("data", exist_ok=True)

    while True:
        await asyncio.sleep(BATCH_SAVE_SECONDS)

        if queue.empty():
            continue

        messages_to_save = []
        while not queue.empty():
            try:
                messages_to_save.append(queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if not messages_to_save:
            continue

        try:
            df = pd.DataFrame(messages_to_save)
            # Use SAVE_FILE (no 'S')
            file_exists = os.path.exists(SAVE_FILE)

            async with aiofiles.open(SAVE_FILE, mode='a', newline='', encoding='utf-8') as f:
                # Add all columns for robustness
                all_cols = [
                    "timestamp", "author", "original_message",
                    "cleaned_message", "sentiment_label", "sentiment_score",
                    "toxicity_label", "toxicity_score", "error"
                ]
                df_to_save = df.reindex(columns=all_cols)
                
                await f.write(df_to_save.to_csv(
                    header=not file_exists,
                    index=False
                ))

            log.info(f"💾 Saved {len(messages_to_save)} messages to {SAVE_FILE}")

        except Exception as e:
            log.error(f"❌ Error saving batch to CSV: {e}")

# --- Lifespan (Your code here is perfect) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Server is starting up")
    try:
        load_models()
        log.info("🧠 NLP models loaded successfully.")
    except Exception as e:
        log.critical(f"❌ FATAL: Could not load NLP models. {e}")
        return # Stop startup if models fail
    
    global saver_task
    saver_task = asyncio.create_task(batch_saver(message_queue))
    yield
    log.info("Server shutting down...")
    if not message_queue.empty():
        log.info("Saving remaining messages in queue...")
        await batch_saver(message_queue)
    saver_task.cancel()
    try:
        await saver_task
    except asyncio.CancelledError:
        log.info("Batch saver task cancelled.")

# --- App Setup (Your code here is perfect) ---
app = FastAPI(lifespan=lifespan)

# Optional: Add CORS if your dashboard will be on a different domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

class ChatMessage(BaseModel):
    user: str
    text: str

class StreamInfo(BaseModel):
    url: str

@app.get("/")
def read_root():
    return {"Message": "Sentiment Analysis API is running."}


@app.post("/set_stream")
async def set_stream(stream: StreamInfo):
    """
    Called from bot.py when a new YouTube video link is entered.
    Creates a new timestamped CSV filename for saving chat data.
    """
    global SAVE_FILE

    # Extract YouTube video ID
    video_id = None
    if "v=" in stream.url:
        video_id = stream.url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in stream.url:
        video_id = stream.url.split("youtu.be/")[1].split("?")[0]

    if not video_id:
        return {"error": "Invalid YouTube URL."}

    # Create data directory
    os.makedirs("data", exist_ok=True)

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    SAVE_FILE = f"data/chat_{video_id}_{timestamp}.csv"

    log.info(f"📁 Now saving chats to → {SAVE_FILE}")
    return {"status": "ok", "file": SAVE_FILE}

# --- FIX 3: Changed to @app.post("/fetch_chat") ---
@app.post("/fetch_chat")
async def fetch_chat(msg: ChatMessage, background_tasks: BackgroundTasks):
    
    # --- FIX 4: Added the missing 'run_analysis' function ---
    # This is the non-blocking logic from my previous example
    async def run_analysis(msg: ChatMessage):
        try:
            # Run the "slow" NLP in a separate thread
            analysis = await asyncio.to_thread(analyse_message, msg.text)

            # Add other info
            analysis["timestamp"] = pd.Timestamp.utcnow().isoformat()
            analysis["author"] = msg.user
            analysis["original_message"] = msg.text

            # Add to our fast in-memory queue
            try:
                await message_queue.put(analysis)
                log.info(f"📩 Queued message from {msg.user}. Queue size: {message_queue.qsize()}")
            except asyncio.QueueFull:
                log.warning("🔥 Message queue is full! A message was dropped.")

        except Exception as e:
            log.error(f"❌ Error during analysis task: {e}")

    # Tell FastAPI to run this *after* we return "ok"
    background_tasks.add_task(run_analysis, msg)
    
    # Return an immediate "OK" to the client
    return {"status": "ok", "message": "Message queued for processing."}

# --- Main (Your code here is perfect) ---
if __name__ == "__main__":
    # Use reload=True for development, it auto-restarts when you save
    uvicorn.run("chat:app", host="127.0.0.1", port=8080, reload=True)