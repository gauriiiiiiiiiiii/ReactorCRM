"""
Orchestrates scraping a post and persisting leads to the database.
Runs in a background thread so Flask can stay responsive.
"""
from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timezone

from database.models import db, TrackedPost, Lead
from scraper.linkedin_scraper import LinkedInScraper
from scraper.mock_scraper import mock_post_metadata, mock_reactors, mock_commenters
from leads.scorer import score_lead
from config import Config


def run_extraction(app, post_db_id: int, max_reactors: int = 100, max_commenters: int = 100):
    """Entry point — call from Flask route in a daemon thread."""
    thread = threading.Thread(
        target=_extraction_worker,
        args=(app, post_db_id, max_reactors, max_commenters),
        daemon=True,
    )
    thread.start()
    return thread


def _extraction_worker(app, post_db_id: int, max_reactors: int, max_commenters: int):
    with app.app_context():
        post = db.session.get(TrackedPost, post_db_id)
        if not post:
            return
        post.status = "scraping"
        db.session.commit()

        try:
            asyncio.run(
                _async_extract(app, post_db_id, max_reactors, max_commenters)
            )
        except Exception as e:
            with app.app_context():
                p = db.session.get(TrackedPost, post_db_id)
                if p:
                    p.status = "error"
                    db.session.commit()
            print(f"[Extractor] Error: {e}")


async def _async_extract(app, post_db_id: int, max_reactors: int, max_commenters: int):
    cfg = Config()
    demo_mode = not cfg.LINKEDIN_EMAIL

    with app.app_context():
        post = db.session.get(TrackedPost, post_db_id)
        post_url = post.url

    if demo_mode:
        # No credentials configured — use mock data instantly
        print(f"[Extractor] No LinkedIn credentials found. Running in demo mode.")
        meta = mock_post_metadata(post_url)
        with app.app_context():
            p = db.session.get(TrackedPost, post_db_id)
            p.author_name = meta.get("author_name")
            p.author_profile = meta.get("author_profile")
            p.post_id = meta.get("post_id")
            p.content_snippet = meta.get("content_snippet")
            p.like_count = meta.get("like_count", 0)
            p.comment_count = meta.get("comment_count", 0)
            p.repost_count = meta.get("repost_count", 0)
            db.session.commit()

        _save_leads(app, post_db_id, mock_reactors(min(max_reactors, 20)))
        _save_leads(app, post_db_id, mock_commenters(min(max_commenters, 10)))

        with app.app_context():
            p = db.session.get(TrackedPost, post_db_id)
            p.status = "done"
            p.scraped_at = datetime.now(timezone.utc)
            db.session.commit()
        return

    # Live scraping with real LinkedIn credentials
    scraper = LinkedInScraper(
        email=cfg.LINKEDIN_EMAIL,
        password=cfg.LINKEDIN_PASSWORD,
        headless=cfg.HEADLESS_BROWSER,
        delay_min=cfg.SCRAPE_DELAY_MIN,
        delay_max=cfg.SCRAPE_DELAY_MAX,
    )
    await scraper.start()
    try:
        logged_in = await scraper.login()
        if not logged_in:
            raise RuntimeError("LinkedIn login failed")

        meta = await scraper.scrape_post_metadata(post_url)
        with app.app_context():
            p = db.session.get(TrackedPost, post_db_id)
            p.author_name = meta.get("author_name")
            p.author_profile = meta.get("author_profile")
            p.post_id = meta.get("post_id")
            p.content_snippet = meta.get("content_snippet")
            p.like_count = meta.get("like_count", 0)
            p.comment_count = meta.get("comment_count", 0)
            p.repost_count = meta.get("repost_count", 0)
            db.session.commit()

        reactors = await scraper.scrape_post_reactors(post_url, max_reactors)
        _save_leads(app, post_db_id, reactors)

        commenters = await scraper.scrape_post_commenters(post_url, max_commenters)
        _save_leads(app, post_db_id, commenters)

        with app.app_context():
            p = db.session.get(TrackedPost, post_db_id)
            p.status = "done"
            p.scraped_at = datetime.now(timezone.utc)
            db.session.commit()

    finally:
        await scraper.stop()


def _save_leads(app, post_db_id: int, profiles: list):
    with app.app_context():
        existing_urls = {
            l.profile_url
            for l in Lead.query.filter_by(post_id=post_db_id).all()
        }
        for profile in profiles:
            if profile.get("profile_url") in existing_urls:
                continue
            score, breakdown = score_lead(profile)
            lead = Lead(
                post_id=post_db_id,
                name=profile.get("name"),
                headline=profile.get("headline"),
                location=profile.get("location"),
                profile_url=profile.get("profile_url"),
                profile_image=profile.get("profile_image"),
                connection_degree=profile.get("connection_degree"),
                engagement_type=profile.get("engagement_type"),
                comment_text=profile.get("comment_text"),
                reaction_type=profile.get("reaction_type"),
                score=score,
                score_breakdown=json.dumps(breakdown),
            )
            db.session.add(lead)
        db.session.commit()
