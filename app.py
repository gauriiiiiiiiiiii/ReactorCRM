from __future__ import annotations

import json
import os
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash

from config import Config
from database.models import db, TrackedPost, Lead
from leads.extractor import run_extraction
from leads.exporter import export_leads

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()


# ── Dashboard ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    posts = TrackedPost.query.order_by(TrackedPost.created_at.desc()).all()
    total_leads = Lead.query.count()
    hot  = Lead.query.filter(Lead.score >= 70).count()
    warm = Lead.query.filter(Lead.score >= 45, Lead.score < 70).count()
    cold = Lead.query.filter(Lead.score < 45).count()
    stats = {"total_posts": len(posts), "total_leads": total_leads,
             "hot": hot, "warm": warm, "cold": cold}
    return render_template("index.html", posts=posts, stats=stats)


# ── Posts ──────────────────────────────────────────────────────────────────────
@app.route("/posts")
def posts():
    all_posts = TrackedPost.query.order_by(TrackedPost.created_at.desc()).all()
    demo_mode = not Config.LINKEDIN_EMAIL
    return render_template("posts.html", posts=all_posts, demo_mode=demo_mode)


@app.route("/posts/<int:post_id>")
def post_detail(post_id):
    post  = db.get_or_404(TrackedPost, post_id)
    leads = Lead.query.filter_by(post_id=post_id).order_by(Lead.score.desc()).all()
    hot   = sum(1 for l in leads if l.score >= 70)
    warm  = sum(1 for l in leads if 45 <= l.score < 70)
    cold  = sum(1 for l in leads if l.score < 45)
    return render_template("post_detail.html", post=post, leads=leads,
                           hot=hot, warm=warm, cold=cold)


@app.route("/posts/add", methods=["POST"])
def add_post():
    url   = request.form.get("url", "").strip()
    tags  = request.form.get("tags", "").strip()
    max_r = int(request.form.get("max_reactors", 100))
    max_c = int(request.form.get("max_commenters", 100))

    if not url or "linkedin.com" not in url:
        flash("Please enter a valid LinkedIn post URL.", "error")
        return redirect(url_for("posts"))

    if TrackedPost.query.filter_by(url=url).first():
        flash("This post is already being tracked.", "warning")
        return redirect(url_for("posts"))

    post = TrackedPost(url=url, topic_tags=tags, status="pending")
    db.session.add(post)
    db.session.commit()
    run_extraction(app, post.id, max_r, max_c)
    flash(f"Post added and scraping started (ID #{post.id}).", "success")
    return redirect(url_for("posts"))


@app.route("/posts/<int:post_id>/rescrape", methods=["POST"])
def rescrape_post(post_id):
    post = db.get_or_404(TrackedPost, post_id)
    post.status = "pending"
    db.session.commit()
    run_extraction(app, post_id)
    flash(f"Re-scrape started for post #{post_id}.", "success")
    return redirect(url_for("post_detail", post_id=post_id))


@app.route("/posts/<int:post_id>/delete", methods=["POST"])
def delete_post(post_id):
    post = db.get_or_404(TrackedPost, post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Post and all associated leads deleted.", "success")
    return redirect(url_for("posts"))


# ── Leads ──────────────────────────────────────────────────────────────────────
@app.route("/leads")
def leads():
    post_id       = request.args.get("post_id", type=int)
    status_filter = request.args.get("status", "")
    tier_filter   = request.args.get("tier", "")
    eng_filter    = request.args.get("eng", "")
    search        = request.args.get("q", "").strip()
    page          = request.args.get("page", 1, type=int)

    query = Lead.query
    if post_id:
        query = query.filter_by(post_id=post_id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if eng_filter:
        query = query.filter_by(engagement_type=eng_filter)
    if tier_filter == "hot":
        query = query.filter(Lead.score >= 70)
    elif tier_filter == "warm":
        query = query.filter(Lead.score >= 45, Lead.score < 70)
    elif tier_filter == "cold":
        query = query.filter(Lead.score < 45)
    if search:
        query = query.filter(
            Lead.name.ilike(f"%{search}%") |
            Lead.headline.ilike(f"%{search}%") |
            Lead.company.ilike(f"%{search}%") |
            Lead.location.ilike(f"%{search}%")
        )

    pagination = query.order_by(Lead.score.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    all_posts = TrackedPost.query.all()
    return render_template(
        "leads.html",
        pagination=pagination,
        leads=pagination.items,
        posts=all_posts,
        post_id=post_id,
        status_filter=status_filter,
        tier_filter=tier_filter,
        eng_filter=eng_filter,
        search=search,
    )


@app.route("/leads/<int:lead_id>")
def lead_detail(lead_id):
    lead = db.get_or_404(Lead, lead_id)
    breakdown = {}
    try:
        breakdown = json.loads(lead.score_breakdown or "{}")
    except Exception:
        pass
    return render_template("lead_detail.html", lead=lead, breakdown=breakdown)


@app.route("/leads/<int:lead_id>/update", methods=["POST"])
def update_lead(lead_id):
    lead = db.get_or_404(Lead, lead_id)
    lead.status   = request.form.get("status",   lead.status)
    lead.notes    = request.form.get("notes",    lead.notes)
    lead.email    = request.form.get("email",    lead.email)
    lead.company  = request.form.get("company",  lead.company)
    lead.industry = request.form.get("industry", lead.industry)
    db.session.commit()
    flash("Lead updated.", "success")
    return redirect(url_for("lead_detail", lead_id=lead_id))


# ── Export ─────────────────────────────────────────────────────────────────────
@app.route("/export")
def export():
    post_id = request.args.get("post_id", type=int)
    fmt     = request.args.get("format", "csv")
    path    = export_leads(post_id, fmt, app.config["EXPORTS_DIR"])
    return send_file(path, as_attachment=True)


# ── Settings ───────────────────────────────────────────────────────────────────
@app.route("/settings")
def settings():
    cfg = {
        "LINKEDIN_EMAIL":    Config.LINKEDIN_EMAIL,
        "HEADLESS_BROWSER":  Config.HEADLESS_BROWSER,
        "SCRAPE_DELAY_MIN":  Config.SCRAPE_DELAY_MIN,
        "SCRAPE_DELAY_MAX":  Config.SCRAPE_DELAY_MAX,
    }
    demo_mode = not Config.LINKEDIN_EMAIL
    return render_template("settings.html", cfg=cfg, demo_mode=demo_mode)


@app.route("/settings/save", methods=["POST"])
def save_settings():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    headless = request.form.get("headless", "true")
    dmin     = request.form.get("delay_min", "2.5")
    dmax     = request.form.get("delay_max", "5.0")

    lines = [
        f"LINKEDIN_EMAIL={email}\n",
        f"LINKEDIN_PASSWORD={password}\n",
        f"HEADLESS_BROWSER={headless}\n",
        f"SCRAPE_DELAY_MIN={dmin}\n",
        f"SCRAPE_DELAY_MAX={dmax}\n",
        f"SECRET_KEY={Config.SECRET_KEY}\n",
    ]
    with open(env_path, "w") as f:
        f.writelines(lines)

    flash("Settings saved. Restart the server for changes to take effect.", "success")
    return redirect(url_for("settings"))


# ── JSON API ───────────────────────────────────────────────────────────────────
@app.route("/api/posts")
def api_posts():
    return jsonify([p.to_dict() for p in TrackedPost.query.all()])


@app.route("/api/posts/<int:post_id>/status")
def api_post_status(post_id):
    post = db.get_or_404(TrackedPost, post_id)
    return jsonify({"status": post.status, "lead_count": len(post.leads)})


@app.route("/api/leads")
def api_leads():
    post_id = request.args.get("post_id", type=int)
    q = Lead.query
    if post_id:
        q = q.filter_by(post_id=post_id)
    return jsonify([l.to_dict() for l in q.order_by(Lead.score.desc()).limit(200).all()])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
