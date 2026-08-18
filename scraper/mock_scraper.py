"""
Mock scraper — generates realistic fake engagement data.
Used automatically when LINKEDIN_EMAIL is not configured in .env,
so the app is fully usable for demos without real credentials.
"""
from __future__ import annotations

import random
import re

FAKE_NAMES = [
    ("Arjun Sharma", "Co-Founder & CEO at FinTech startup | IIM Bangalore '22", "Bangalore"),
    ("Priya Mehta", "MBA Student | Aspiring Entrepreneur | SaaS ideas", "Mumbai"),
    ("Rahul Gupta", "Product Manager at Zomato | Ex-founder", "Delhi"),
    ("Sneha Nair", "Director of Business Development | Startup Enthusiast", "Chennai"),
    ("Vikram Patel", "Angel Investor | Early stage startups | Ex-IIT Bombay", "Pune"),
    ("Ananya Singh", "Founder at GreenTech India | Sustainability | B2B SaaS", "Hyderabad"),
    ("Deepak Kumar", "CTO at stealth startup | Full-stack dev | IIT Delhi", "Noida"),
    ("Riya Joshi", "MBA 2024 | Consulting | Startup ecosystem", "Ahmedabad"),
    ("Manish Verma", "Head of Growth | D2C brands | Previously Meesho", "Bangalore"),
    ("Kavya Reddy", "Venture Capital Analyst | IIM Calcutta", "Bangalore"),
    ("Saurav Das", "Final year B.Tech | Building my first product", "Kolkata"),
    ("Nisha Kapoor", "Marketing Manager | Consumer brands | Ex-HUL", "Delhi"),
    ("Aditya Bhatt", "VP Engineering | Series A startup | Cloud infra", "Gurgaon"),
    ("Pooja Iyer", "UI/UX Designer | Freelance | EdTech products", "Kochi"),
    ("Harsh Agarwal", "CEO & Founder at AgriTech | IIM Lucknow Alumni", "Lucknow"),
    ("Divya Krishnan", "Business Analyst | McKinsey | Startup advisor", "Bangalore"),
    ("Rohan Malhotra", "CTO & Co-founder | AI startup | IIT Bombay", "Mumbai"),
    ("Simran Bose", "Founder @ Edutech | Former teacher | Social impact", "Kolkata"),
    ("Nikhil Jain", "VP Sales | B2B SaaS | 8 years in enterprise sales", "Pune"),
    ("Aisha Khan", "Entrepreneur | Women in Tech | Product @ Razorpay", "Bangalore"),
    ("Karthik Subramanian", "Investor @ Blume Ventures | ex-Flipkart", "Bangalore"),
    ("Tanvi Desai", "Student Entrepreneur | IIM Indore | E-commerce", "Indore"),
    ("Pranav Nair", "Head of Product | Series B Startup | Ex-Amazon", "Hyderabad"),
    ("Shruti Agarwal", "Operations Lead | Supply chain | Interested in startups", "Delhi"),
    ("Rohit Bansal", "Growth Hacker | Digital Marketing | Startup junkie", "Gurgaon"),
]

COMMENTS = [
    "This is exactly what I was looking for! How can I apply? Please DM me.",
    "Interested! I have been working on a SaaS idea. Would love to connect.",
    "Can someone share the registration link? Very interested.",
    "Great initiative! Please share how to register and join.",
    "Love this! Would be great to learn from industry mentors. How do I apply?",
    "I want to apply for this. Is there an application form?",
    "This is a great opportunity. How do I join the next cohort?",
    "Very insightful post! Would love to learn more about this programme.",
    "Congrats on this launch! Sharing with my network.",
    "This is brilliant. DM me if there are spots still available.",
    "How do we register? Is it open for final year students?",
    "Reach out to me if you need more founders for the cohort!",
]

REACTIONS = ["Like", "Celebrate", "Support", "Insightful", "Love", "Like", "Like", "Insightful"]
DEGREES = ["1st", "2nd", "2nd", "2nd", "3rd", "3rd"]


def mock_post_metadata(url: str) -> dict:
    # Derive a stable, URL-unique id so the TrackedPost.post_id unique
    # constraint is never violated when the URL has no embedded activity id.
    post_id = _extract_post_id(url) or f"mock{abs(hash(url)) % (10 ** 12)}"
    return {
        "url": url,
        "post_id": post_id,
        "author_name": "IIM Entrepreneurship Programme",
        "author_profile": "https://www.linkedin.com/company/iim-ep/",
        "content_snippet": (
            "We are thrilled to announce the launch of our new Entrepreneurship "
            "Programme! Join us to build the next big startup. Apply now and be "
            "part of India's leading startup ecosystem. Limited seats available."
        ),
        "like_count": random.randint(150, 400),
        "comment_count": random.randint(30, 80),
        "repost_count": random.randint(5, 25),
    }


def mock_reactors(n: int = 20) -> list[dict]:
    pool = random.sample(FAKE_NAMES, min(n, len(FAKE_NAMES)))
    result = []
    for name, headline, location in pool:
        result.append({
            "name": name,
            "headline": headline,
            "location": location,
            "profile_url": f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}/",
            "profile_image": None,
            "engagement_type": "liked",
            "reaction_type": random.choice(REACTIONS),
            "comment_text": None,
            "connection_degree": random.choice(DEGREES),
        })
    return result


def mock_commenters(n: int = 10) -> list[dict]:
    pool = random.sample(FAKE_NAMES, min(n, len(FAKE_NAMES)))
    result = []
    for name, headline, location in pool:
        result.append({
            "name": name,
            "headline": headline,
            "location": location,
            "profile_url": f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}-c/",
            "profile_image": None,
            "engagement_type": "commented",
            "reaction_type": None,
            "comment_text": random.choice(COMMENTS),
            "connection_degree": random.choice(DEGREES),
        })
    return result


def _extract_post_id(url: str) -> str | None:
    match = re.search(r"-(\d{10,})-", url)
    return match.group(1) if match else None
