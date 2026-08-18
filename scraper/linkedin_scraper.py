"""
LinkedIn scraper using Playwright browser automation.
Uses the user's own LinkedIn session (via cookie import or manual login).
Respects rate limits with randomized delays to avoid detection.
"""
import asyncio
import json
import random
import re
import time
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext


class LinkedInScraper:
    LOGIN_URL = "https://www.linkedin.com/login"
    BASE_URL = "https://www.linkedin.com"

    def __init__(self, email: str, password: str, headless: bool = True,
                 delay_min: float = 2.0, delay_max: float = 5.0):
        self.email = email
        self.password = password
        self.headless = headless
        self.delay_min = delay_min
        self.delay_max = delay_max
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
        self._logged_in = False

    async def _random_delay(self):
        await asyncio.sleep(random.uniform(self.delay_min, self.delay_max))

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        self._page = await self._context.new_page()

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def load_cookies(self, cookies: list):
        """Load pre-saved LinkedIn session cookies to skip login."""
        await self._context.add_cookies(cookies)
        self._logged_in = True

    async def login(self) -> bool:
        """Log in to LinkedIn with email/password."""
        if not self.email or not self.password:
            raise ValueError("LinkedIn credentials not configured.")
        try:
            await self._page.goto(self.LOGIN_URL, wait_until="networkidle")
            await self._page.fill("#username", self.email)
            await self._page.fill("#password", self.password)
            await self._random_delay()
            await self._page.click('button[type="submit"]')
            await self._page.wait_for_url("**/feed/**", timeout=15000)
            self._logged_in = True
            return True
        except Exception as e:
            print(f"[Scraper] Login failed: {e}")
            return False

    async def get_cookies(self) -> list:
        return await self._context.cookies()

    # ------------------------------------------------------------------
    # Post metadata
    # ------------------------------------------------------------------
    async def scrape_post_metadata(self, post_url: str) -> dict:
        """Return author, snippet, like/comment counts for a post URL."""
        if not self._logged_in:
            raise RuntimeError("Not logged in.")
        await self._page.goto(post_url, wait_until="domcontentloaded")
        await self._random_delay()

        data = {
            "url": post_url,
            "post_id": self._extract_post_id(post_url),
            "author_name": None,
            "author_profile": None,
            "content_snippet": None,
            "like_count": 0,
            "comment_count": 0,
            "repost_count": 0,
            "scraped_at": datetime.utcnow().isoformat(),
        }

        try:
            # Author name
            author_el = await self._page.query_selector(
                ".update-components-actor__title span[aria-hidden='true']"
            )
            if author_el:
                data["author_name"] = (await author_el.inner_text()).strip()

            # Author profile URL
            author_link = await self._page.query_selector(
                ".update-components-actor__container a"
            )
            if author_link:
                data["author_profile"] = await author_link.get_attribute("href")

            # Post content
            content_el = await self._page.query_selector(
                ".feed-shared-update-v2__description span[dir]"
            )
            if content_el:
                text = await content_el.inner_text()
                data["content_snippet"] = text[:500]

            # Reaction / like count
            like_el = await self._page.query_selector(
                ".social-details-social-counts__reactions-count"
            )
            if like_el:
                data["like_count"] = self._parse_count(await like_el.inner_text())

            # Comment count
            comment_el = await self._page.query_selector(
                "button.social-details-social-counts__comments"
            )
            if comment_el:
                data["comment_count"] = self._parse_count(await comment_el.inner_text())

            # Repost count
            repost_el = await self._page.query_selector(
                "button.social-details-social-counts__item--with-social-proof"
            )
            if repost_el:
                text = await repost_el.inner_text()
                if "repost" in text.lower():
                    data["repost_count"] = self._parse_count(text)

        except Exception as e:
            print(f"[Scraper] Error parsing post metadata: {e}")

        return data

    # ------------------------------------------------------------------
    # Reactions (likers)
    # ------------------------------------------------------------------
    async def scrape_post_reactors(self, post_url: str, max_results: int = 100) -> list:
        """Scrape profiles of people who reacted to a post."""
        if not self._logged_in:
            raise RuntimeError("Not logged in.")

        post_id = self._extract_post_id(post_url)
        if not post_id:
            return []

        reactors_url = (
            f"https://www.linkedin.com/feed/reactions/detail/"
            f"?activityId={post_id}&reactionType=ALL"
        )
        await self._page.goto(reactors_url, wait_until="domcontentloaded")
        await self._random_delay()

        reactors = []
        seen_profiles = set()
        scroll_attempts = 0
        max_scrolls = max(5, max_results // 10)

        while len(reactors) < max_results and scroll_attempts < max_scrolls:
            cards = await self._page.query_selector_all(
                ".social-details-reactors-modal__reactor-list-item"
            )
            for card in cards:
                profile = await self._extract_reactor_card(card)
                if profile and profile.get("profile_url") not in seen_profiles:
                    seen_profiles.add(profile["profile_url"])
                    reactors.append(profile)
                    if len(reactors) >= max_results:
                        break

            # Scroll modal
            modal = await self._page.query_selector(".social-details-reactors-modal__content")
            if modal:
                await modal.evaluate("el => el.scrollTop += 800")
            await self._random_delay()
            scroll_attempts += 1

        return reactors

    async def _extract_reactor_card(self, card) -> Optional[dict]:
        try:
            link = await card.query_selector("a.app-aware-link")
            name_el = await card.query_selector(
                ".social-details-reactors-modal__reactor-name"
            )
            headline_el = await card.query_selector(
                ".social-details-reactors-modal__reactor-title"
            )
            reaction_el = await card.query_selector(
                ".reactions-modal__reaction-icon-container img"
            )
            img_el = await card.query_selector("img.presence-entity__image")

            profile_url = await link.get_attribute("href") if link else None
            name = (await name_el.inner_text()).strip() if name_el else None
            headline = (await headline_el.inner_text()).strip() if headline_el else None
            reaction_type = (
                await reaction_el.get_attribute("alt") if reaction_el else "Like"
            )
            profile_image = await img_el.get_attribute("src") if img_el else None

            return {
                "name": name,
                "headline": headline,
                "profile_url": self._clean_profile_url(profile_url),
                "profile_image": profile_image,
                "engagement_type": "liked",
                "reaction_type": reaction_type,
                "comment_text": None,
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------
    async def scrape_post_commenters(self, post_url: str, max_results: int = 100) -> list:
        """Scrape profiles and comment text of people who commented on a post."""
        if not self._logged_in:
            raise RuntimeError("Not logged in.")

        await self._page.goto(post_url, wait_until="domcontentloaded")
        await self._random_delay()

        # Click "load more comments"
        for _ in range(3):
            load_more = await self._page.query_selector(
                "button.comments-comments-list__load-more-comments-button"
            )
            if not load_more:
                break
            await load_more.click()
            await self._random_delay()

        commenters = []
        seen = set()

        comment_els = await self._page.query_selector_all(
            ".comments-comment-item"
        )
        for el in comment_els[:max_results]:
            commenter = await self._extract_comment(el)
            if commenter and commenter.get("profile_url") not in seen:
                seen.add(commenter["profile_url"])
                commenters.append(commenter)

        return commenters

    async def _extract_comment(self, el) -> Optional[dict]:
        try:
            link = await el.query_selector(
                ".comments-post-meta__actor-link"
            )
            name_el = await el.query_selector(
                ".comments-post-meta__name span[aria-hidden='true']"
            )
            headline_el = await el.query_selector(
                ".comments-post-meta__headline"
            )
            text_el = await el.query_selector(
                ".comments-comment-item__main-content"
            )
            img_el = await el.query_selector("img.ivm-view-attr__img--centered")

            profile_url = await link.get_attribute("href") if link else None
            name = (await name_el.inner_text()).strip() if name_el else None
            headline = (await headline_el.inner_text()).strip() if headline_el else None
            comment_text = (await text_el.inner_text()).strip() if text_el else None
            profile_image = await img_el.get_attribute("src") if img_el else None

            return {
                "name": name,
                "headline": headline,
                "profile_url": self._clean_profile_url(profile_url),
                "profile_image": profile_image,
                "engagement_type": "commented",
                "reaction_type": None,
                "comment_text": comment_text,
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_post_id(url: str) -> Optional[str]:
        # Format: /posts/...-XXXXXXXXXXXXXXX-XXXX/
        match = re.search(r"-(\d{19})-", url)
        if match:
            return match.group(1)
        # Format: /feed/update/urn:li:activity:XXXXXXXX
        match = re.search(r"urn:li:activity:(\d+)", url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _clean_profile_url(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        if url.startswith("/"):
            return f"https://www.linkedin.com{url.split('?')[0]}"
        return url.split("?")[0]

    @staticmethod
    def _parse_count(text: str) -> int:
        text = text.strip().lower().replace(",", "")
        match = re.search(r"([\d.]+)\s*([km]?)", text)
        if not match:
            return 0
        num = float(match.group(1))
        suffix = match.group(2)
        if suffix == "k":
            num *= 1000
        elif suffix == "m":
            num *= 1_000_000
        return int(num)
