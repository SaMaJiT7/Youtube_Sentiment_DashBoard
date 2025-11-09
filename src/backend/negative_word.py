NEGATIVE_WORDS = {
    "idiot", "stupid", "dumb", "moron", "noob", "trash",
    "garbage", "worthless", "useless", "terrible", "awful", "horrible",
    "disgusting", "ugly", "pathetic", "lame", "loser", "clown",
    "hate", "kill", "die", "suicide", "burn", "toxic", "annoying",
    "bastard", "bitch", "fuck", "shit", "crap", "jerk", "asshole",
    "liar", "cheater", "scammer", "retard", "sucks", "crazy", "insane"
}

def detect_negative_words(text: str):
    """
    Returns a list of negative words found in the text (case-insensitive)
    """
    text = text.lower()
    matches = [w for w in NEGATIVE_WORDS if w in text]
    return matches