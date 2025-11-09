🔴 Live YouTube Chat Sentiment Dashboard

This project is a real-time system that fetches live chat from any YouTube stream, performs sentiment and toxicity analysis on each message, and displays the results on a live Streamlit dashboard.

It is built with a 3-Terminal system:

Server (chat.py): A FastAPI server that loads the NLP models and handles analysis.

Client (bot.py): A client that fetches chat from YouTube and sends it to the server.

Dashboard (dashboard.py): A Streamlit app that visualizes the saved data.

🚀 How to Run This Project

1. Setup

# Clone the repository (or download the ZIP)
git clone [https://github.com/SaMaJiT7/Youtube_Sentiment_DashBoard.git](https://github.com/SaMaJiT7/Youtube_Sentiment_DashBoard.git)
cd YOUTUBE_Toxicity_Dashboard

# Create and activate a virtual environment
python -m venv bot
bot\Scripts\activate

# Install all required libraries
pip install -r requirements.txt

# Create your .env file
# Go to the 'src/' folder
cd src
# Rename '.env.example' to '.env'
ren .env.example .env
# Edit the .env file and paste your YouTube API Key


2. Run the 3 Terminals

You must run these in the correct order, from your src/ folder.

Terminal 1: Run the SERVER ("Brain")

# From the src/ folder
uvicorn fastapi_server:app --port 8080


Wait for it to say: INFO: Application startup complete.

Terminal 2: Run the CLIENT ("Fetcher")
(Open a new terminal and activate your bot venv)

# From the src/ folder
python bot.py


It will ask for a live YouTube URL. Paste one in.

Terminal 3: Run the DASHBOARD ("Face")
(Open a third terminal and activate your bot venv)

# From the src/ folder
streamlit run dashboard.py


Your browser will open to http://localhost:8501 and the live dashboard will appear!