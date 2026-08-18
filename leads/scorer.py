"""
Lead scoring engine.
Scores each lead 0-100 based on engagement quality and profile signals.
"""
from __future__ import annotations

import json


WEIGHTS = {
    "engagement_type": {
        "commented": 40,
        "reposted": 25,
        "liked": 10,
    },
    "reaction_type": {
        "Insightful": 8,
        "Love": 6,
        "Celebrate": 5,
        "Support": 5,
        "Like": 3,
        "Funny": 1,
    },
    "connection_degree": {
        "1st": 15,
        "2nd": 10,
        "3rd": 5,
    },
    "comment_keywords": {
        "interested": 5,
        "contact": 5,
        "how": 3,
        "where": 3,
        "more info": 5,
        "reach out": 5,
        "connect": 4,
        "learn more": 5,
        "sign up": 6,
        "join": 4,
        "apply": 6,
        "register": 6,
        "dm": 5,
        "message": 4,
        "email": 4,
    },
}

ICP_KEYWORDS = [
    "founder", "ceo", "cto", "entrepreneur", "startup",
    "head of", "director", "vp ", "vice president",
    "product manager", "growth", "business development",
    "investor", "venture", "angel",
    "student", "mba", "iim", "iit",
]


def score_lead(lead_data: dict) -> tuple[float, dict]:
    """
    Returns (score: float, breakdown: dict).
    lead_data keys: engagement_type, reaction_type, connection_degree,
                    comment_text, headline
    """
    breakdown = {}
    total = 0.0

    # Engagement type (base)
    eng = lead_data.get("engagement_type", "liked")
    eng_score = WEIGHTS["engagement_type"].get(eng, 5)
    breakdown["engagement_type"] = eng_score
    total += eng_score

    # Reaction type bonus
    reaction = lead_data.get("reaction_type") or ""
    reaction_score = WEIGHTS["reaction_type"].get(reaction, 0)
    breakdown["reaction_type"] = reaction_score
    total += reaction_score

    # Connection degree
    degree = lead_data.get("connection_degree", "3rd")
    degree_score = WEIGHTS["connection_degree"].get(degree, 3)
    breakdown["connection_degree"] = degree_score
    total += degree_score

    # Comment quality
    comment = (lead_data.get("comment_text") or "").lower()
    comment_score = 0
    matched_kws = []
    for kw, pts in WEIGHTS["comment_keywords"].items():
        if kw in comment:
            comment_score += pts
            matched_kws.append(kw)
    comment_score = min(comment_score, 25)   # cap at 25
    breakdown["comment_keywords"] = comment_score
    breakdown["matched_keywords"] = matched_kws
    total += comment_score

    # ICP profile match
    headline = (lead_data.get("headline") or "").lower()
    icp_score = 0
    matched_icp = []
    for kw in ICP_KEYWORDS:
        if kw in headline:
            icp_score += 4
            matched_icp.append(kw)
    icp_score = min(icp_score, 12)
    breakdown["icp_match"] = icp_score
    breakdown["matched_icp"] = matched_icp
    total += icp_score

    score = min(round(total, 1), 100.0)
    return score, breakdown


def score_tier(score: float) -> str:
    if score >= 70:
        return "hot"
    if score >= 45:
        return "warm"
    return "cold"
