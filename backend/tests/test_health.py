"""Smoke tests – run with: pytest backend/tests -q (API must be importable)."""

def test_intelligence_sentiment():
    from app.services.intelligence import classify_sentiment, classify_topics
    label, score = classify_sentiment("Great progress on Lagos roads and development")
    assert label in ("positive", "neutral", "mixed")
    topics = classify_topics("Traffic and road potholes in Ikeja")
    assert "roads" in topics or "transportation" in topics


def test_narrative_detection():
    from app.services.narrative import detect_narratives, suggest_response
    result = detect_narratives([
        "This is a failed government with corruption everywhere",
        "Vote them out – rigged system",
        "Progress and delivery on infrastructure gives hope",
    ])
    assert "narratives" in result
    assert "misinfo_risk" in result
    s = suggest_response("opposition")
    assert "action" in s


def test_badges():
    from app.services.badges import compute_badges
    badges = compute_badges(5, 55.0, [])
    codes = {b["code"] for b in badges}
    assert "first_report" in codes or "consistent_5" in codes


def test_password_hash():
    from app.core.security import get_password_hash, verify_password
    h = get_password_hash("TestPassword1!")
    assert verify_password("TestPassword1!", h)
    assert not verify_password("wrong", h)
