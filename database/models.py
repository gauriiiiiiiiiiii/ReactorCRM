from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class TrackedPost(db.Model):
    __tablename__ = "tracked_posts"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), unique=True, nullable=False)
    post_id = db.Column(db.String(200), unique=True)
    author_name = db.Column(db.String(200))
    author_profile = db.Column(db.String(500))
    content_snippet = db.Column(db.Text)
    topic_tags = db.Column(db.String(500))   # comma-separated
    like_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    repost_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default="pending")  # pending/scraping/done/error
    scraped_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    leads = db.relationship("Lead", backref="post", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "post_id": self.post_id,
            "author_name": self.author_name,
            "content_snippet": self.content_snippet,
            "topic_tags": self.topic_tags,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "repost_count": self.repost_count,
            "status": self.status,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "lead_count": len(self.leads),
        }


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("tracked_posts.id"), nullable=False)

    # Profile info
    name = db.Column(db.String(300))
    headline = db.Column(db.String(500))
    location = db.Column(db.String(300))
    profile_url = db.Column(db.String(500))
    profile_image = db.Column(db.String(500))
    connection_degree = db.Column(db.String(10))   # 1st, 2nd, 3rd

    # Engagement
    engagement_type = db.Column(db.String(50))   # liked / commented / reposted
    comment_text = db.Column(db.Text)
    reaction_type = db.Column(db.String(50))     # Like/Celebrate/Support/Funny/Love/Insightful

    # Lead score (0-100)
    score = db.Column(db.Float, default=0.0)
    score_breakdown = db.Column(db.Text)   # JSON string

    # CRM-style fields
    status = db.Column(db.String(50), default="new")  # new/contacted/qualified/converted/rejected
    notes = db.Column(db.Text)
    email = db.Column(db.String(200))
    company = db.Column(db.String(300))
    industry = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "name": self.name,
            "headline": self.headline,
            "location": self.location,
            "profile_url": self.profile_url,
            "profile_image": self.profile_image,
            "connection_degree": self.connection_degree,
            "engagement_type": self.engagement_type,
            "comment_text": self.comment_text,
            "reaction_type": self.reaction_type,
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "status": self.status,
            "notes": self.notes,
            "email": self.email,
            "company": self.company,
            "industry": self.industry,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
