"""
Lightweight intelligence stubs – no heavy GPU models on 8GB VPS.
Rule-based sentiment + topic classification suitable for CPU.
Replace with sentence-transformers / local LLM when resources allow.
"""

import re
from typing import List, Tuple

POSITIVE = {
    "good", "great", "excellent", "progress", "development", "hope", "support",
    "win", "success", "proud", "love", "thank", "appreciate", "better", "improve",
    "achievement", "deliver", "promise kept", "infrastructure",
}
NEGATIVE = {
    "bad", "fail", "failure", "corrupt", "corruption", "lie", "lies", "scam",
    "hate", "angry", "poor", "worse", "crisis", "protest", "rig", "steal",
    "incompetent", "useless", "disaster", "suffering", "unemployment",
}
TOPIC_KEYWORDS = {
    "economy": ["economy", "jobs", "employment", "unemployment", "inflation", "naira", "business"],
    "roads": ["road", "roads", "highway", "pothole", "traffic", "transport"],
    "housing": ["housing", "rent", "landlord", "shelter", "estate"],
    "education": ["school", "education", "teacher", "student", "university"],
    "healthcare": ["hospital", "health", "doctor", "clinic", "medicine"],
    "security": ["security", "crime", "police", "kidnap", "safety"],
    "governance": ["governance", "government", "policy", "leadership", "accountability"],
    "transportation": ["bus", "train", "ferry", "brt", "lagbus", "transport"],
}


def detect_language(text: str) -> str:
    # Very rough heuristic
    if not text:
        return "unknown"
    lower = text.lower()
    if any(w in lower for w in ["ni", "wa", "fun", "si", "ati", "ko"]):
        # could be Yoruba mix – still mark en for simplicity
        pass
    return "en"


def classify_sentiment(text: str) -> Tuple[str, float]:
    if not text:
        return "neutral", 0.5
    tokens = set(re.findall(r"[a-zA-Z']+", text.lower()))
    pos = len(tokens & POSITIVE)
    neg = len(tokens & NEGATIVE)
    total = pos + neg
    if total == 0:
        return "neutral", 0.5
    score = pos / total
    if pos > neg and score >= 0.6:
        return "positive", round(score, 2)
    if neg > pos and score <= 0.4:
        return "negative", round(1 - score, 2)
    if pos and neg:
        return "mixed", 0.5
    return "neutral", 0.5


def classify_topics(text: str) -> List[str]:
    if not text:
        return []
    lower = text.lower()
    found = []
    for topic, kws in TOPIC_KEYWORDS.items():
        if any(k in lower for k in kws):
            found.append(topic)
    return found[:5]


def match_keywords(text: str, keywords: List[str]) -> List[str]:
    if not text or not keywords:
        return []
    lower = text.lower()
    return [k for k in keywords if k.lower() in lower]


def bot_heuristic(author_handle: str | None, content: str | None, engagement: dict | None) -> bool:
    """Simple bot suspicion signals – not definitive."""
    if not author_handle:
        return False
    handle = author_handle.lower()
    if re.search(r"\d{5,}", handle):
        return True
    if content and len(content) < 5:
        return True
    eng = engagement or {}
    if eng.get("followers", 1000) < 10 and eng.get("posts", 0) > 500:
        return True
    return False
