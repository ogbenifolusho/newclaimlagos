"""
Narrative & misinformation detection stubs.
Rule/heuristic based for 8GB VPS – swap for LLM/RAG when resources allow.
"""

import re
from typing import List, Dict, Any
from collections import Counter

COORDINATION_SIGNALS = [
    r"retweet\s+this",
    r"copy\s+and\s+paste",
    r"everyone\s+post",
    r"#\w+\s+#\w+\s+#\w+",  # hashtag flooding pattern
]

FALSE_CLAIM_PATTERNS = [
    r"confirmed:\s*all\s+\w+\s+are",
    r"breaking:\s*\w+\s+has\s+fled",
    r"secret\s+video\s+shows",
    r"they\s+don'?t\s+want\s+you\s+to\s+see",
    r"100%\s+proof",
]

OPPOSITION_CUES = ["rigged", "stolen mandate", "never again", "vote them out", "failed government"]
POSITIVE_CUES = ["progress", "delivery", "fulfilled", "development", "hope", "continuity"]


def detect_narratives(texts: List[str]) -> Dict[str, Any]:
    """Aggregate narrative signals from a batch of post texts."""
    joined = " ".join(t.lower() for t in texts if t)
    opp = sum(1 for c in OPPOSITION_CUES if c in joined)
    pos = sum(1 for c in POSITIVE_CUES if c in joined)
    coord_hits = sum(1 for t in texts for p in COORDINATION_SIGNALS if re.search(p, t or "", re.I))
    false_hits = sum(1 for t in texts for p in FALSE_CLAIM_PATTERNS if re.search(p, t or "", re.I))

    narratives = []
    if opp >= 2:
        narratives.append({"type": "opposition", "strength": min(opp / 5, 1.0), "label": "Opposition narrative rising"})
    if pos >= 2:
        narratives.append({"type": "positive", "strength": min(pos / 5, 1.0), "label": "Positive delivery narrative"})
    if coord_hits:
        narratives.append({"type": "coordinated", "strength": min(coord_hits / 3, 1.0), "label": "Possible coordinated amplification"})
    if false_hits:
        narratives.append({"type": "misinfo_risk", "strength": min(false_hits / 2, 1.0), "label": "Misinformation risk signals"})

    risk = "low"
    if false_hits or coord_hits >= 2:
        risk = "high"
    elif opp >= 3 or coord_hits:
        risk = "medium"

    return {
        "narratives": narratives,
        "misinfo_risk": risk,
        "misinfo_confidence": round(min(0.3 + false_hits * 0.2 + coord_hits * 0.15, 0.95), 2),
        "sample_size": len(texts),
        "method": "heuristic_v1",
    }


def suggest_response(narrative_type: str) -> Dict[str, str]:
    templates = {
        "opposition": {
            "action": "counter_narrative",
            "draft_hint": "Acknowledge concerns, present verified delivery facts, invite scrutiny of official data.",
            "spokesperson": "Director of New Media / Issue owner",
        },
        "misinfo_risk": {
            "action": "fact_check_and_counter",
            "draft_hint": "Issue clear factual correction with sources. Do not amplify false claim wording.",
            "spokesperson": "Official campaign spokesperson",
        },
        "coordinated": {
            "action": "monitor_and_escalate",
            "draft_hint": "Increase monitoring window. Prepare rapid response pack. Avoid reactive pile-on.",
            "spokesperson": "Situation Room Manager",
        },
        "positive": {
            "action": "amplify",
            "draft_hint": "Package verified success stories for Ambassador distribution after approval.",
            "spokesperson": "Content Manager",
        },
    }
    return templates.get(narrative_type, {
        "action": "monitor",
        "draft_hint": "Continue monitoring and update Situation Room.",
        "spokesperson": "Intelligence Officer",
    })
