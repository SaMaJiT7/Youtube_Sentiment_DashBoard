import streamlit as st
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import os
import time
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="YouTube Livechat Sentiment Dashboard",
    page_icon="🎮",
    layout="wide"
)

# --- Filepath ---
# This is the "pointer" file that bot.py creates
CONFIG_FILE = "current_stream.txt"

# --- Run the auto-refresher ---
# This will re-run the *entire* script every 5 seconds. This is perfect.
st_autorefresh(interval=5000, key="datarefresh")

def get_csv_name():

    if not os.path.exists(CONFIG_FILE):
        return None
    
    try:
        with open(CONFIG_FILE, "r") as f:
            return f.read().strip()
    except Exception as e:
        st.error(f"Error reading config file {CONFIG_FILE}: {e}")
        return None
    

@st.cache_data(ttl=5)
def load_data(csv_filename):

    if not csv_filename:
        st.warning("⚠️ Waiting for the `bot.py` client to start a new stream...")
        return pd.DataFrame() # Return empty table
    

    if not os.path.exists(csv_filename):
        st.warning(f"⚠️ Waiting for data... (File not found: {csv_filename})")
        return pd.DataFrame(columns=[
            "timestamp", "author", "original_message", "cleaned_message",
            "sentiment_label", "sentiment_score", "toxicity_label", "toxicity_score"
        ])
    
    try:
        df = pd.read_csv(csv_filename)
        if df.empty:
            return df
        
        # Convert types
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['sentiment_score'] = pd.to_numeric(df['sentiment_score'], errors='coerce')
        df['toxicity_score'] = pd.to_numeric(df['toxicity_score'], errors='coerce')
        return df
    except pd.errors.EmptyDataError:
        return pd.DataFrame() # File is empty, just wait
    except Exception as e:
        st.error(f"Error loading data from {csv_filename}: {e}")
        return pd.DataFrame()

    
def generate_wordcloud(text_series):
    """Generates a word cloud from a pandas series of text."""
    if text_series.empty or text_series.isnull().all():
        return None
        
    # Join all messages into one big string
    text = " ".join(str(msg) for msg in text_series.dropna())
    
    if not text:
        return None

    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color="black",
        colormap="coolwarm",
        max_words=200,
        collocations=False
    ).generate(text)
    
    return wordcloud


#----MAIN DashBoard----

st.title("🎮 Live YouTube Chat Sentiment Dashboard")

DATA_FILE_NAME = get_csv_name()
st.info(f"Watching file: {DATA_FILE_NAME}")

#Load the Data
data = load_data(DATA_FILE_NAME)

if data.empty:
    st.warning("No chat data found yet. Is the `bot.py` client running and sending messages to the server?")
    st.stop() # Tell streamlit to stop here and wait for the refresh



# --- Top Row: Key Metrics ---
st.header("📊 Key Metrics")

if data is not None and not data.empty:
    # Calculate main stats safely
    total_messages = len(data)
    avg_sentiment = data['sentiment_score'].mean() if 'sentiment_score' in data else 0
    total_toxic_msgs = len(data[data['toxicity_label'] == 'TOXIC']) if 'toxicity_label' in data else 0
    toxicity_percent = (total_toxic_msgs / total_messages) * 100 if total_messages > 0 else 0

    # Display 4 metrics side by side
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("💬 Total Messages", f"{total_messages}")
    col2.metric("😊 Avg. Sentiment", f"{avg_sentiment:.2f}")
    col3.metric("☠️ Toxic Messages", f"{total_toxic_msgs}")
    col4.metric("⚠️ Toxicity %", f"{toxicity_percent:.2f}%")

else:
    st.warning("⚠️ No chat data available yet. Please start the bot or load a CSV file.")


#----MIDDLE ROW : Charts----

st.header("📈 Live Charts")

col_left, col_right = st.columns(2)

with col_left:
    # Chart 1: Sentiment Over Time
    st.subheader("Sentiment Over Time")
    if not data.empty:
        # Resample to 10-second intervals for smoother line
        sentiment_over_time = (
            data.set_index('timestamp')
            .resample('10s')
            .agg({'sentiment_score': 'mean'})
            .reset_index()
        )

        fig_sentiment = px.line(
            sentiment_over_time,
            x='timestamp',
            y='sentiment_score',
            title="Average Sentiment (10-second intervals)"
        )
        fig_sentiment.update_layout(
            xaxis_title="Time",
            yaxis_title="Sentiment Score (-1 to 1)",
            title_x=0.2
        )
        st.plotly_chart(fig_sentiment, width='stretch')
    else:
        st.write("No data yet to plot sentiment trend.")

with col_right:
    st.subheader("Top Toxic Users")
    toxic_data = data[data['toxicity_label'] == 'TOXIC']

    if not toxic_data.empty:
        top_toxic_users = (
            toxic_data['author']
            .value_counts()
            .nlargest(10)
            .reset_index()
        )
        top_toxic_users.columns = ['User', 'Toxic Message Count']

        fig_toxic_users = px.bar(
            data_frame=top_toxic_users,
            x='Toxic Message Count',
            y='User',
            orientation='h',
            title="Users with Most Toxic Messages",
            color='Toxic Message Count',
            color_continuous_scale='Reds'
        )

        fig_toxic_users.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            title_x=0.2
        )

        st.plotly_chart(fig_toxic_users, width='stretch')
    else:
        st.write("No toxic messages detected yet.")


# --- Bottom Row: Word Cloud & Raw Data ---
st.header("💬 Message Analysis")
col_cloud, col_raw = st.columns(2)

with col_cloud:
    # Word Cloud of common (cleaned) words
    st.subheader("Common Words")
    wordcloud_fig = generate_wordcloud(data['cleaned_message'])
    if wordcloud_fig:
        fig, ax = plt.subplots()
        ax.imshow(wordcloud_fig, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)
    else:
        st.write("Not enough data for a word cloud.")

with col_raw:
    # Raw Data Table
    st.subheader("Latest Messages")
    # Show the *last* 10 messages, in reverse order (newest on top)
    st.dataframe(data.tail(10).iloc[::-1][["timestamp", "author", "original_message", "sentiment_label", "toxicity_label"]])

