import re
import emoji
import warnings
from transformers import pipeline, logging as hf_logging

from backend.negative_word import detect_negative_words

# Suppress warnings
hf_logging.set_verbosity_error()

# --- Globals to hold the models ---
sentiment_pipeline = None
toxicity_pipeline = None

def load_models():
    """
    Loads the Hugging Face models into the global variables.
    """
    global sentiment_pipeline, toxicity_pipeline
    
    print("🧠 -> Loading Sentiment Model (twitter-roberta)...")
    sentiment_pipeline = pipeline(
        "sentiment-analysis", # type: ignore
        model="cardiffnlp/twitter-roberta-base-sentiment",
        device=-1 # -1 for CPU, 0 for GPU
    ) # type: ignore
    
    print("🧠 -> Loading Toxicity Model (toxic-bert)...")
    toxicity_pipeline = pipeline(
        "text-classification",
        model="unitary/toxic-bert",
        # Use top_k=None to get all scores
        top_k=None,
        device=-1 # -1 for CPU, 0 for GPU
    )
    print("🧠 -> Models loaded successfully.")

def remove_urls(text):
    url_pattern = r'https?://\S+|www\.\S+'
    clean_text = re.sub(url_pattern, '', text)
    return clean_text

def remove_non_alpha(text):
    clean_text = re.sub(r'[^a-zA-Z\s?]', '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def clean_text(message:str) -> str: # type: ignore
    if not isinstance(message, str):
        return ""
    msg = emoji.demojize(message)
    msg = remove_urls(msg)
    msg = remove_non_alpha(msg)
    msg = msg.lower().strip()
    return msg

# --- (Using your 'analyse' spelling) ---
def analyse_message(raw_message:str) -> dict:

    if not sentiment_pipeline or not toxicity_pipeline:
        print("❌ ERROR: Models are not loaded. Please call load_models() first.")
        return {
            "original_message": raw_message,
            "error": "Models are not loaded."
        }

    cleaned_text = clean_text(raw_message)

    negative_hits = detect_negative_words(cleaned_text)

    if not cleaned_text:
        return {
            "original_message": raw_message,
            "cleaned_message": "",
            "sentiment_label": "NEUTRAL",
            "sentiment_score": 0.0,
            "toxicity_label": "NOT_TOXIC",
            "toxicity_score": 0.0,
            "error": "Empty message"
        }

    try:
        sentiment = sentiment_pipeline(cleaned_text)[0]

        # --- THIS IS THE FINAL, 100% FIX ---
        # We add [0] to get the *inner list* of scores
        tox_results_list = toxicity_pipeline(cleaned_text)[0]
        # ---
    
        sentiment_label = sentiment['label']
        sentiment_score = sentiment['score']

        if sentiment_label == 'LABEL_0':
            sentiment_label = "NEGATIVE"
            sentiment_score = -sentiment_score
        elif sentiment_label == 'LABEL_1':
            sentiment_label = "NEUTRAL"
            sentiment_score = 0.0
        else:
            sentiment_label = "POSITIVE"
        
        toxicity_score = 0.0
        # Now, 'result' will be a dict {'label':...}, not a list
        for result in tox_results_list:
            if result['label'] == 'toxic': # type: ignore # This will work
                toxicity_score = result['score'] # type: ignore
                break
        
        if toxicity_score > 0.5: # type: ignore
            toxicity_label = "TOXIC"
        else:
            toxicity_label = "NOT_TOXIC"

        

        if negative_hits and toxicity_score < 0.8: # type: ignore
            toxicity_score += 0.2 # type: ignore
            toxicity_score = min(toxicity_score, 1.0)
            toxicity_label = "toxic" if toxicity_score >= 0.5 else "non-toxic"

        
        
        return {
            "original_message": raw_message,
            "cleaned_message": cleaned_text,
            "sentiment_label": sentiment_label,
            "sentiment_score": sentiment_score,
            "toxicity_label": toxicity_label,
            "toxicity_score": toxicity_score,
            "contains_negative_word": len(negative_hits) > 0,
            "error": None
        }

    except Exception as e:
        print(f"Error during analysis: {e}")
        return {
            "original_message": raw_message,
            "cleaned_message": cleaned_text,
            "error": str(e)
        }

# --- Test (if you run this file directly) ---
if __name__ == "__main__":
    print("--- Testing NLP model file ---")
    load_models()
    
    test_msgs = [
        "This is awesome!",
        "I hate this, it's so bad 😠",
        "POG LULW THATS SO BAD",
        "you are a stupid idiot, go away",
        "http://spam-link.com",
        "Just a normal comment.",
        "koi bat nahi aap kro live me betha hu"
    ]
    
    for msg in test_msgs:
        print(f"\n--- Original: {msg} ---")
        analysis = analyse_message(msg)
        import json
        print(json.dumps(analysis, indent=4))