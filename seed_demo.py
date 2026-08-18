"""
Seed the database with realistic demo data so the UI is usable
without running a live LinkedIn scrape.
Run: python seed_demo.py
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone, timedelta
from app import app
from database.models import db, TrackedPost, Lead
from leads.scorer import score_lead

DEMO_POSTS = [
    {
        "url": "https://www.linkedin.com/posts/iim-entrepreneurship-programme-share-7310133419177340928-Wnf8/",
        "post_id": "7310133419177340928",
        "author_name": "IIM Entrepreneurship Programme",
        "content_snippet": "We are thrilled to announce the launch of our new Entrepreneurship Programme! Join us to build the next big startup from IIM. Apply now and be part of India's leading startup ecosystem.",
        "topic_tags": "entrepreneurship, iim, startup, education",
        "like_count": 312,
        "comment_count": 47,
        "repost_count": 18,
        "status": "done",
    },
    {
        "url": "https://www.linkedin.com/posts/setu-startup-school-activity-7290000000000000001-demo/",
        "post_id": "7290000000000000001",
        "author_name": "SETU Startup School",
        "content_snippet": "Looking for passionate founders ready to build the next unicorn? SETU Startup School is now accepting applications for our 2024 cohort. Drop a comment below if you're interested!",
        "topic_tags": "startup, founders, cohort",
        "like_count": 180,
        "comment_count": 63,
        "repost_count": 9,
        "status": "done",
    },
]

DEMO_PROFILES = [
    {"name": "Arjun Sharma", "headline": "Co-Founder & CEO at FinTech startup | IIM Bangalore '22", "location": "Bangalore", "engagement_type": "commented", "reaction_type": None, "comment_text": "This is exactly what I was looking for! How can I apply? Please DM me more info."},
    {"name": "Priya Mehta", "headline": "MBA Student | Aspiring Entrepreneur | Looking to launch my startup", "location": "Mumbai", "engagement_type": "commented", "reaction_type": None, "comment_text": "Interested! I have been working on a SaaS idea for the past 6 months. Would love to connect."},
    {"name": "Rahul Gupta", "headline": "Product Manager at Zomato | Ex-founder", "location": "Delhi", "engagement_type": "liked", "reaction_type": "Insightful", "comment_text": None},
    {"name": "Sneha Nair", "headline": "Director of Business Development | Startup Enthusiast", "location": "Chennai", "engagement_type": "commented", "reaction_type": None, "comment_text": "Can someone share the registration link? Very interested in this programme."},
    {"name": "Vikram Patel", "headline": "Angel Investor | Early stage startups | Ex-IIT Bombay", "location": "Pune", "engagement_type": "reposted", "reaction_type": None, "comment_text": None},
    {"name": "Ananya Singh", "headline": "Founder at GreenTech India | Sustainability | B2B SaaS", "location": "Hyderabad", "engagement_type": "commented", "reaction_type": None, "comment_text": "Great initiative! Please share how to register and join the next cohort."},
    {"name": "Deepak Kumar", "headline": "CTO at stealth startup | Full-stack dev | IIT Delhi", "location": "Noida", "engagement_type": "liked", "reaction_type": "Celebrate", "comment_text": None},
    {"name": "Riya Joshi", "headline": "MBA 2024 | Consulting | Startup ecosystem", "location": "Ahmedabad", "engagement_type": "liked", "reaction_type": "Like", "comment_text": None},
    {"name": "Manish Verma", "headline": "Head of Growth | D2C brands | Previously Meesho", "location": "Bangalore", "engagement_type": "commented", "reaction_type": None, "comment_text": "Love this! Would be great to learn from industry mentors. How do I apply?"},
    {"name": "Kavya Reddy", "headline": "Venture Capital Analyst | Early-stage investments | IIM Calcutta", "location": "Bangalore", "engagement_type": "liked", "reaction_type": "Insightful", "comment_text": None},
    {"name": "Saurav Das", "headline": "Student | Final year B.Tech | Building my first product", "location": "Kolkata", "engagement_type": "commented", "reaction_type": None, "comment_text": "I am a student but really want to join this. Is it open for undergrads?"},
    {"name": "Nisha Kapoor", "headline": "Marketing Manager | Consumer brands | Ex-HUL", "location": "Delhi", "engagement_type": "liked", "reaction_type": "Love", "comment_text": None},
    {"name": "Aditya Bhatt", "headline": "VP Engineering | Series A startup | Cloud infrastructure", "location": "Gurgaon", "engagement_type": "reposted", "reaction_type": None, "comment_text": None},
    {"name": "Pooja Iyer", "headline": "UI/UX Designer | Freelance | EdTech products", "location": "Kochi", "engagement_type": "liked", "reaction_type": "Support", "comment_text": None},
    {"name": "Harsh Agarwal", "headline": "CEO & Founder at AgriTech | IIM Lucknow Alumni", "location": "Lucknow", "engagement_type": "commented", "reaction_type": None, "comment_text": "This is a great opportunity. Please share more info — I want to apply for my second venture."},
]

def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset.")

        for i, pd in enumerate(DEMO_POSTS):
            post = TrackedPost(**pd)
            scraped = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72))
            post.scraped_at = scraped
            db.session.add(post)
            db.session.flush()

            # Assign profiles to this post (split them)
            subset = DEMO_PROFILES if i == 0 else random.sample(DEMO_PROFILES, 8)
            for profile in subset:
                score, breakdown = score_lead(profile)
                lead = Lead(
                    post_id=post.id,
                    name=profile["name"],
                    headline=profile["headline"],
                    location=profile.get("location"),
                    profile_url=f"https://www.linkedin.com/in/{profile['name'].lower().replace(' ', '-')}/",
                    engagement_type=profile["engagement_type"],
                    reaction_type=profile.get("reaction_type"),
                    comment_text=profile.get("comment_text"),
                    score=score,
                    score_breakdown=json.dumps(breakdown),
                    status=random.choice(["new", "new", "new", "contacted", "qualified"]),
                    connection_degree=random.choice(["1st", "2nd", "2nd", "3rd"]),
                )
                db.session.add(lead)

        db.session.commit()
        print(f"Seeded {len(DEMO_POSTS)} posts and demo leads successfully.")
        print("Run: python app.py  ->  http://127.0.0.1:5000")

if __name__ == "__main__":
    seed()
