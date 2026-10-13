"""
Badge rules for Digital Ambassadors.
Awarded on report completion / performance thresholds.
"""

BADGE_RULES = [
    {"code": "first_report", "name": "First Report", "min_completed": 1},
    {"code": "consistent_5", "name": "Consistent (5 tasks)", "min_completed": 5},
    {"code": "reliable_15", "name": "Reliable (15 tasks)", "min_completed": 15},
    {"code": "champion_50", "name": "Champion (50 tasks)", "min_completed": 50},
    {"code": "score_50", "name": "Rising Star", "min_score": 50},
    {"code": "score_80", "name": "Top Performer", "min_score": 80},
]


def compute_badges(completed_tasks: int, performance_score: float, existing: list | None = None) -> list:
    existing_codes = {b.get("code") for b in (existing or []) if isinstance(b, dict)}
    badges = list(existing or [])
    for rule in BADGE_RULES:
        code = rule["code"]
        if code in existing_codes:
            continue
        if "min_completed" in rule and completed_tasks >= rule["min_completed"]:
            badges.append({"code": code, "name": rule["name"]})
            existing_codes.add(code)
        if "min_score" in rule and performance_score >= rule["min_score"]:
            badges.append({"code": code, "name": rule["name"]})
            existing_codes.add(code)
    return badges
