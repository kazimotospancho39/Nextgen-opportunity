from __future__ import annotations

import os
import secrets
import smtplib
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()
database_url = os.getenv("DATABASE_URL", "sqlite:///opportunity_hub_global.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32),
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=100_000_000,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
PAYMENT_CURRENCY = os.getenv("PAYMENT_CURRENCY", "USD").strip().upper()
PAYMENT_OPTIONS = "card, mobilemoneytanzania" if PAYMENT_CURRENCY == "TZS" else "card"

CATEGORIES = {
    "scholarship": "Scholarships",
    "fellowship": "Fellowships",
    "internship": "Internships",
    "job": "Jobs & careers",
    "event": "Conferences & events",
    "camp": "Camps & leadership",
    "grant": "Grants & competitions",
    "training": "Training & exchange",
}
REGIONS = {
    "africa": ("Africa", "Kenya", "Ghana", "Tanzania", "Uganda", "Rwanda", "Nigeria", "South Africa", "Ethiopia", "Nairobi", "Cape Town"),
    "americas": ("Americas", "United States", "USA", "Canada", "Brazil", "Mexico"),
    "asia": ("Asia", "India", "Singapore", "Japan", "Malaysia", "Philippines"),
    "europe": ("Europe", "Portugal", "United Kingdom", "UK", "France", "Germany", "Netherlands"),
    "mena": ("Middle East", "North Africa", "Morocco", "Egypt", "Jordan"),
    "online": ("online", "remote", "virtual", "worldwide"),
}
PAGES = {"home": "Homepage", "about": "About Opportunity Hub", "programs": "Programs & services", "contact": "Contact"}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(40), nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    location = db.Column(db.String(120), nullable=False, default="Worldwide · Online")
    level = db.Column(db.String(80), nullable=False, default="All levels")
    deadline = db.Column(db.String(100), nullable=False, default="Open until filled")
    summary = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)
    eligibility = db.Column(db.Text, nullable=False, default="See program details below.")
    benefits = db.Column(db.Text, nullable=False, default="")
    application_fee_tzs = db.Column(db.Integer, nullable=False, default=0)
    featured = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    event_type = db.Column(db.String(60), nullable=False, default="Community event")
    start_at = db.Column(db.String(100), nullable=False)
    end_at = db.Column(db.String(100), nullable=False, default="")
    location = db.Column(db.String(180), nullable=False, default="Worldwide · Online")
    summary = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    capacity = db.Column(db.Integer, nullable=False, default=100)
    ticket_price_tzs = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, nullable=False, index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunity.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    statement = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Submitted")
    payment_status = db.Column(db.String(20), nullable=False, default="not_required")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    opportunity = db.relationship("Opportunity")
    user = db.relationship("User")


class EventRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    payment_status = db.Column(db.String(20), nullable=False, default="not_required")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    event = db.relationship("Event")
    user = db.relationship("User")


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(48), unique=True, nullable=False, index=True)
    owner_type = db.Column(db.String(24), nullable=False)
    owner_id = db.Column(db.Integer, nullable=False)
    amount_tzs = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    status = db.Column(db.String(20), nullable=False, default="pending")
    gateway_transaction_id = db.Column(db.String(60), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class SavedOpportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunity.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "opportunity_id"),)
    opportunity = db.relationship("Opportunity")


class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    topic = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class PageSection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(40), nullable=False, index=True)
    section_key = db.Column(db.String(80), nullable=False)
    label = db.Column(db.String(120), nullable=False)
    value = db.Column(db.Text, nullable=False)
    __table_args__ = (db.UniqueConstraint("page", "section_key"),)


class MediaItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    caption = db.Column(db.String(500), nullable=False, default="")
    media_type = db.Column(db.String(12), nullable=False)
    file_path = db.Column(db.String(255), nullable=False, unique=True)
    show_on_home = db.Column(db.Boolean, nullable=False, default=False)
    show_in_gallery = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class ContentMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.String(24), nullable=False, index=True)
    content_key = db.Column(db.String(180), nullable=False, index=True)
    media_id = db.Column(db.Integer, db.ForeignKey("media_item.id", ondelete="CASCADE"), nullable=False)
    media = db.relationship("MediaItem")
    __table_args__ = (db.UniqueConstraint("content_type", "content_key", "media_id"),)


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}


def content_media_for(content_type: str, content_key: str | int) -> list[MediaItem]:
    links = ContentMedia.query.filter_by(content_type=content_type, content_key=str(content_key)).order_by(ContentMedia.id).all()
    return [link.media for link in links if link.media]


def content_uploads_are_valid(files) -> bool:
    uploads = [f for f in files if f and f.filename]
    invalid = [f for f in uploads if Path(secure_filename(f.filename)).suffix.lower() not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS]
    if invalid:
        flash("Media files must be JPG, PNG, WebP, GIF, MP4, WebM or MOV.", "error")
        return False
    return True


def attach_content_uploads(files, content_type: str, content_key: str | int, caption: str = "") -> None:
    uploads = [f for f in files if f and f.filename]
    if not uploads:
        return
    relative_dir = Path("uploads") / "media"
    upload_dir = Path(app.static_folder) / relative_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    for upload in uploads:
        clean_name = secure_filename(upload.filename)
        extension = Path(clean_name).suffix.lower()
        stored_name = f"{secrets.token_hex(16)}{extension}"
        upload.save(upload_dir / stored_name)
        item = MediaItem(title=Path(clean_name).stem[:180], caption=caption.strip()[:500], media_type="photo" if extension in IMAGE_EXTENSIONS else "video",
                         file_path=(relative_dir / stored_name).as_posix(), show_on_home=False, show_in_gallery=False)
        db.session.add(item)
        db.session.flush()
        db.session.add(ContentMedia(content_type=content_type, content_key=str(content_key), media=item))


def slugify(text: str) -> str:
    base = "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in text).split())[:150] or "item"
    return f"{base}-{secrets.token_hex(3)}"


def seed_data():
    if PageSection.query.first():
        return
    sections = [
        ("home", "eyebrow", "Hero eyebrow", "OPPORTUNITY HAS NO BORDERS"),
        ("home", "headline", "Homepage headline", "A world of opportunity.\nA future you shape."),
        ("home", "intro", "Homepage introduction", "Discover scholarships, careers, leadership programs and events for young people everywhere — then apply, register and track your progress in one global hub."),
        ("home", "impact", "Impact statement", "Find a path that fits. Then make it yours."),
        ("about", "headline", "About headline", "Opportunity should not depend on who you know."),
        ("about", "body", "About description", "Opportunity Hub is an independent global platform connecting young people with learning, work, funding and experiences. Discover, prepare, apply and keep your progress in one place."),
        ("programs", "headline", "Programs headline", "Explore more than a listing."),
        ("programs", "body", "Programs description", "Browse opportunities, join leadership programs, register for events, save your next steps and track your applications from one personal dashboard."),
        ("contact", "headline", "Contact headline", "Talk to the Opportunity Hub team."),
        ("contact", "body", "Contact description", "Questions about opportunities, partnerships or accessibility? Send a message to our team from this page."),
    ]
    db.session.add_all(PageSection(page=p, section_key=k, label=l, value=v) for p, k, l, v in sections)
    if not Opportunity.query.first():
        db.session.add_all([
            Opportunity(slug="global-youth-leadership-lab", title="Global Youth Leadership Lab", category="camp", location="Lisbon, Portugal · International cohort", level="Ages 18–35 · All countries", deadline="Applications close 15 December 2026", summary="A hands-on leadership and community innovation experience bringing young people together across borders.", description="Join an original Opportunity Hub demonstration program built around creative problem-solving, community projects and peer learning. Participants learn together, work in small teams and leave with a project plan and a cross-cultural network.", eligibility="Open to young people aged 18–35 of all nationalities. Participants should be available for the full program and meet travel requirements for the host country.", benefits="Facilitated workshops\nProject design support\nPeer mentor circles\nCompletion certificate", featured=True),
            Opportunity(slug="global-future-scholars-award", title="Global Future Scholars Award", category="scholarship", location="Multiple host countries · Worldwide applicants", level="Undergraduate & postgraduate", deadline="Applications close 20 January 2027", summary="Study support for motivated students with a clear plan for learning, growth and community contribution.", description="A demonstration scholarship listing for international students. Applicants submit their education background and a statement about their learning goals. Award details, eligible countries and conditions should be confirmed by the Opportunity Hub before publication.", eligibility="Applicants from all countries who are enrolled or preparing to enroll in an accredited degree program. Academic standing and a personal statement are required.", benefits="Tuition support\nAcademic planning workshop\nPeer support network", featured=True),
            Opportunity(slug="digital-futures-global-internship", title="Digital Futures Global Internship", category="internship", location="Online · Global cohort", level="Students & recent graduates", deadline="Rolling review", summary="Build experience in research, digital communications and community technology with an international mentor team.", description="A practical eight-week remote placement supporting public-interest digital projects. Interns collaborate on research, content and service design while receiving regular guidance and feedback.", eligibility="Open worldwide to students and recent graduates interested in technology for community benefit. Strong written communication and reliable internet access are required.", benefits="Eight-week mentored placement\nPortfolio-ready project work\nInternational peer network", featured=False),
            Opportunity(slug="community-action-microgrant", title="Community Action Starter Grant", category="grant", location="Cape Town, South Africa · Africa-wide applicants", level="Teams of 2–5 · Ages 18–35", deadline="Applications close 31 January 2027", summary="Seed support for youth-led ideas improving wellbeing, inclusion or environmental resilience in local communities.", description="Teams can propose a focused 90-day project with a clear community need, feasible activities and a simple way to measure progress. Selected teams receive a microgrant and remote coaching.", eligibility="Teams led by young people aged 18–35 living in any African country. Proposals should identify a community partner and realistic delivery plan.", benefits="Seed funding\nThree online coaching sessions\nRegional showcase opportunity", featured=False),
            Opportunity(slug="international-public-service-fellowship", title="International Public Service Fellowship", category="fellowship", location="Singapore · Asia-Pacific cohort", level="Early-career professionals", deadline="Applications close 5 February 2027", summary="A guided fellowship for emerging changemakers working on inclusive education, climate action and stronger communities.", description="A flexible fellowship combining skill sessions, peer circles and a mentored community project. Fellows build practical skills and an international network while contributing to a local challenge.", eligibility="Applicants from Asia-Pacific countries with an interest in public service, community work or sustainable development. No prior fellowship is required.", benefits="Mentor circles\nProject coaching\nProfessional development sessions", featured=False),
            Opportunity(slug="north-america-social-impact-placement", title="Social Impact Career Placement", category="job", location="Montreal, Canada · North American applicants", level="Recent graduates & early-career applicants", deadline="Applications close 18 February 2027", summary="A paid early-career placement supporting inclusive community programs and social innovation research.", description="Join a small cross-functional team for a six-month placement in community partnerships, research and communications. The role includes structured mentoring and practical project ownership.", eligibility="Applicants authorized to work in Canada or eligible for a relevant work permit. Applications are welcomed from candidates with diverse academic and professional backgrounds.", benefits="Paid six-month placement\nMentor support\nProfessional development budget", featured=False),
            Opportunity(slug="mena-culture-and-leadership-exchange", title="Culture & Leadership Exchange", category="training", location="Marrakech, Morocco · Middle East & North Africa", level="Ages 18–32", deadline="Applications close 28 February 2027", summary="A cross-cultural learning exchange exploring community leadership, creative practice and shared regional challenges.", description="Participants take part in workshops, peer discussions and a collaborative local project. Sessions connect cultural exchange with practical approaches to community leadership.", eligibility="Applicants aged 18–32 from Middle Eastern and North African countries. Working knowledge of English, French or Arabic is helpful.", benefits="Facilitated workshops\nCommunity project visit\nCross-border peer network", featured=False),
        ])
    if not Event.query.first():
        db.session.add_all([
            Event(slug="global-opportunity-clinic", title="Design Your Next Step: Global Opportunity Clinic", event_type="Career workshop", start_at="22 November 2026 · 10:00 UTC", end_at="1:00 PM UTC", location="Online · Join from anywhere", summary="A friendly, practical workshop to strengthen your opportunity search and international application plan.", description="Bring a goal or opportunity you are considering. Work through eligibility, timelines and application planning with peers and mentors from around the world.", capacity=250, ticket_price_tzs=0),
            Event(slug="world-changemakers-forum", title="World Changemakers Forum", event_type="Youth forum", start_at="12 December 2026 · 9:30 UTC", end_at="4:00 PM UTC", location="Hybrid · Nairobi & online worldwide", summary="A global day of youth-led conversations and collaborative problem-solving on livelihoods, climate and community wellbeing.", description="Hear community stories, join a facilitated idea lab and meet people working on local solutions. Join online or in person in Nairobi.", capacity=500, ticket_price_tzs=15),
            Event(slug="cross-culture-story-lab", title="Cross-Culture Story Lab", event_type="Cultural exchange", start_at="16 January 2027 · 2:00 PM UTC", end_at="4:00 PM UTC", location="Online · International participants", summary="Share a story, learn a new perspective and build connections across cultures in a welcoming online gathering.", description="Small-group prompts and creative activities help participants exchange experiences and build empathy across borders. No special equipment or experience needed.", capacity=200, ticket_price_tzs=0),
        ])
    db.session.commit()


@app.context_processor
def inject_site_context():
    user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
    return {"categories": CATEGORIES, "regions": REGIONS, "site_user": user, "is_admin": bool(session.get("admin")), "page_names": PAGES, "payment_currency": PAYMENT_CURRENCY, "money": format_money, "countdown_datetime": countdown_datetime}


def format_money(value: int, currency: str | None = None) -> str:
    currency = (currency or PAYMENT_CURRENCY).upper()
    amount = int(value or 0)
    if currency in {"USD", "EUR", "GBP"}:
        return f"{currency} {amount:,.2f}"
    return f"{currency} {amount:,}"


def countdown_datetime(value: str, end_of_day: bool = False) -> str:
    """Parse dates used in listings and return an explicit UTC instant."""
    import re

    match = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2})(?:\s+(?:at\s+)?(\d{1,2}:\d{2}(?:\s*[APap][Mm])?))?", (value or "").replace("·", " "))
    if not match:
        return ""
    date_text, time_text = match.groups()
    parsed_date = None
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%B %d, %Y", "%b %d %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            parsed_date = datetime.strptime(date_text, fmt).date()
            break
        except ValueError:
            continue
    if parsed_date is None:
        return ""
    if time_text:
        cleaned_time = re.sub(r"\s+", " ", time_text.upper()).strip()
        formats = ("%I:%M %p",) if "M" in cleaned_time else ("%H:%M",)
        parsed_time = None
        for fmt in formats:
            try:
                parsed_time = datetime.strptime(cleaned_time, fmt).time()
                break
            except ValueError:
                continue
        if parsed_time is None:
            return ""
    else:
        parsed_time = time(23, 59, 59) if end_of_day else time(0, 0)
    return datetime.combine(parsed_date, parsed_time, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def countdown_expired(value: str, end_of_day: bool = False) -> bool:
    instant = countdown_datetime(value, end_of_day)
    if not instant:
        return False
    return datetime.fromisoformat(instant.replace("Z", "+00:00")) <= datetime.now(timezone.utc)


def page_copy(page: str) -> dict[str, str]:
    return {s.section_key: s.value for s in PageSection.query.filter_by(page=page).all()}


def make_payment(owner_type: str, owner_id: int, amount_tzs: int) -> Payment:
    payment = Payment(reference=f"OH-{secrets.token_hex(8).upper()}", owner_type=owner_type, owner_id=owner_id, amount_tzs=amount_tzs, currency=PAYMENT_CURRENCY)
    db.session.add(payment)
    db.session.flush()
    if owner_type == "application":
        record = db.session.get(Application, owner_id)
        record.payment_status = "pending"
    else:
        record = db.session.get(EventRegistration, owner_id)
        record.payment_status = "pending"
    return payment


def send_member_alert(subject: str, body: str):
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_FROM_EMAIL", "").strip()
    if not all((host, username, password, sender)):
        return
    try:
        with smtplib.SMTP_SSL(host, int(os.getenv("SMTP_PORT", "465")), timeout=15) as server:
            server.login(username, password)
            for subscriber in Subscriber.query.order_by(Subscriber.id).all():
                message = EmailMessage()
                message["Subject"] = subject
                message["From"] = sender
                message["To"] = subscriber.email
                message.set_content(body)
                server.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError):
        app.logger.exception("Could not send opportunity email alerts")


@app.route("/")
def home():
    category = request.args.get("category", "")
    region = request.args.get("region", "")
    q = request.args.get("q", "").strip()
    query = Opportunity.query.filter_by(active=True)
    if category in CATEGORIES:
        query = query.filter_by(category=category)
    if region in REGIONS:
        query = query.filter(or_(*[
            field.ilike(f"%{term}%")
            for field in (Opportunity.location, Opportunity.summary, Opportunity.description, Opportunity.eligibility)
            for term in REGIONS[region]
        ]))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Opportunity.title.ilike(like), Opportunity.summary.ilike(like), Opportunity.location.ilike(like), Opportunity.description.ilike(like)))
    else:
        query = query.order_by(Opportunity.featured.desc(), Opportunity.created_at.desc())
    return render_template("home.html", opportunities=query.limit(8).all(), events=Event.query.filter_by(active=True).order_by(Event.start_at).limit(3).all(), media_items=MediaItem.query.filter_by(show_on_home=True).order_by(MediaItem.created_at.desc()).limit(4).all(), page_media=content_media_for("page", "home"), copy=page_copy("home"), selected_category=category, selected_region=region, search=q, counts={"opportunities": Opportunity.query.filter_by(active=True).count(), "events": Event.query.filter_by(active=True).count()})


@app.get("/opportunities")
def opportunities():
    """Search the full active global opportunity directory."""
    category = request.args.get("category", "")
    region = request.args.get("region", "")
    level = request.args.get("level", "").strip()
    mode = request.args.get("mode", "")
    cost = request.args.get("cost", "")
    deadline_filter = request.args.get("deadline", "")
    q = request.args.get("q", "").strip()

    query = Opportunity.query.filter_by(active=True)
    if category in CATEGORIES:
        query = query.filter_by(category=category)
    if region in REGIONS:
        query = query.filter(or_(*[
            field.ilike(f"%{term}%")
            for field in (Opportunity.location, Opportunity.summary, Opportunity.description, Opportunity.eligibility)
            for term in REGIONS[region]
        ]))
    if level:
        query = query.filter(Opportunity.level.ilike(f"%{level}%"))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Opportunity.title.ilike(like), Opportunity.summary.ilike(like), Opportunity.location.ilike(like), Opportunity.description.ilike(like), Opportunity.eligibility.ilike(like)))

    items = query.order_by(Opportunity.featured.desc(), Opportunity.created_at.desc()).all()
    if mode in {"online", "in_person"}:
        online_terms = ("online", "remote", "virtual", "worldwide")
        items = [item for item in items if any(term in item.location.lower() for term in online_terms) == (mode == "online")]
    if cost == "free":
        items = [item for item in items if not item.application_fee_tzs]
    elif cost == "paid":
        items = [item for item in items if item.application_fee_tzs]
    if deadline_filter == "open":
        items = [item for item in items if not countdown_expired(item.deadline, True)]
    elif deadline_filter == "closing_soon":
        now = datetime.now(timezone.utc)
        items = [item for item in items if (lambda instant: instant is not None and now < instant <= now + timedelta(days=30))(datetime.fromisoformat(countdown_datetime(item.deadline, True).replace("Z", "+00:00")) if countdown_datetime(item.deadline, True) else None)]
    return render_template("opportunities.html", opportunities=items, selected_category=category, selected_region=region, selected_level=level, selected_mode=mode, selected_cost=cost, selected_deadline=deadline_filter, search=q)


@app.get("/gallery")
def gallery():
    items = MediaItem.query.filter_by(show_in_gallery=True).order_by(MediaItem.created_at.desc()).all()
    return render_template("gallery.html", media_items=items)


@app.get("/about")
def about():
    return render_template("info.html", page="about", copy=page_copy("about"), page_title=PAGES["about"], page_media=content_media_for("page", "about"))


@app.get("/programs")
def programs():
    return render_template("info.html", page="programs", copy=page_copy("programs"), page_title=PAGES["programs"], page_media=content_media_for("page", "programs"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        message = request.form.get("message", "").strip()
        if not name or "@" not in email or not message:
            flash("Please enter your name, a valid email, and a message.", "error")
        else:
            db.session.add(ContactMessage(name=name, email=email, topic=request.form.get("topic", "Something else")[:80], message=message[:5000]))
            db.session.commit()
            flash("Thanks — your message has been received by the Opportunity Hub team.", "success")
    return render_template("contact.html", copy=page_copy("contact"), page_media=content_media_for("page", "contact"))


@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()
    if "@" not in email or len(email) > 254:
        flash("Enter a valid email address to join opportunity alerts.", "error")
    elif not Subscriber.query.filter_by(email=email).first():
        db.session.add(Subscriber(email=email))
        db.session.commit()
        flash("You're on the list. Look out for new opportunities and events.", "success")
    else:
        flash("This email is already signed up for updates.", "info")
    return redirect(url_for("home") + "#alerts")


@app.route("/opportunities/<slug>")
def opportunity_detail(slug):
    item = Opportunity.query.filter_by(slug=slug, active=True).first_or_404()
    saved = bool(session.get("user_id") and SavedOpportunity.query.filter_by(user_id=session["user_id"], opportunity_id=item.id).first())
    return render_template("opportunity.html", item=item, saved=saved, content_media=content_media_for("opportunity", item.id), deadline_closed=countdown_expired(item.deadline, True))


@app.post("/opportunities/<slug>/save")
def save_opportunity(slug):
    if not session.get("user_id"):
        flash("Sign in to keep opportunities on your personal board.", "info")
        return redirect(url_for("login", next=url_for("opportunity_detail", slug=slug)))
    user_id = session["user_id"]
    item = Opportunity.query.filter_by(slug=slug, active=True).first_or_404()
    saved = SavedOpportunity.query.filter_by(user_id=user_id, opportunity_id=item.id).first()
    if saved:
        db.session.delete(saved)
        flash("Removed from your saved opportunities.", "success")
    else:
        db.session.add(SavedOpportunity(user_id=user_id, opportunity_id=item.id))
        flash("Saved to your personal opportunity board.", "success")
    db.session.commit()
    return redirect(url_for("opportunity_detail", slug=slug))


@app.route("/opportunities/<slug>/apply", methods=["GET", "POST"])
def apply(slug):
    item = Opportunity.query.filter_by(slug=slug, active=True).first_or_404()
    if countdown_expired(item.deadline, True):
        flash("The application window for this opportunity has closed.", "info")
        return redirect(url_for("opportunity_detail", slug=slug))
    if not session.get("user_id"):
        flash("Create an account or sign in to start your application.", "info")
        return redirect(url_for("login", next=url_for("apply", slug=slug)))
    if request.method == "POST":
        statement = request.form.get("statement", "").strip()
        if len(statement) < 80 or len(statement) > 5000:
            flash("Your statement should be between 80 and 5,000 characters.", "error")
            return render_template("apply.html", item=item)
        user = db.session.get(User, session["user_id"])
        record = Application(reference=f"OH-APP-{secrets.token_hex(5).upper()}", opportunity=item, user=user, statement=statement, payment_status="not_required" if not item.application_fee_tzs else "pending")
        db.session.add(record)
        db.session.flush()
        if item.application_fee_tzs:
            payment = make_payment("application", record.id, item.application_fee_tzs)
            db.session.commit()
            return redirect(url_for("payment", reference=payment.reference))
        db.session.commit()
        flash("Application received. Track its progress from your dashboard.", "success")
        return redirect(url_for("dashboard"))
    return render_template("apply.html", item=item)


@app.get("/events")
def events():
    return render_template("events.html", events=Event.query.filter_by(active=True).order_by(Event.start_at).all())


@app.get("/events/<slug>")
def event_detail(slug):
    event = Event.query.filter_by(slug=slug, active=True).first_or_404()
    registrations = EventRegistration.query.filter_by(event_id=event.id).count()
    return render_template("event.html", event=event, remaining=max(0, event.capacity - registrations), event_started=countdown_expired(event.start_at), content_media=content_media_for("event", event.id))


@app.post("/events/<slug>/register")
def event_register(slug):
    event = Event.query.filter_by(slug=slug, active=True).first_or_404()
    if countdown_expired(event.start_at):
        flash("This event has already started, so registration is closed.", "info")
        return redirect(url_for("event_detail", slug=slug))
    if not session.get("user_id"):
        flash("Sign in or create an account to register for this event.", "info")
        return redirect(url_for("login", next=url_for("event_detail", slug=slug)))
    if EventRegistration.query.filter_by(event_id=event.id, user_id=session["user_id"]).first():
        flash("You already have a registration for this event. Check your dashboard.", "info")
        return redirect(url_for("dashboard"))
    if EventRegistration.query.filter_by(event_id=event.id).count() >= event.capacity:
        flash("This event is full. Join the opportunity alerts for future dates.", "error")
        return redirect(url_for("event_detail", slug=slug))
    record = EventRegistration(reference=f"OH-EVT-{secrets.token_hex(5).upper()}", event=event, user_id=session["user_id"], payment_status="not_required" if not event.ticket_price_tzs else "pending")
    db.session.add(record)
    db.session.flush()
    if event.ticket_price_tzs:
        payment = make_payment("event", record.id, event.ticket_price_tzs)
        db.session.commit()
        return redirect(url_for("payment", reference=payment.reference))
    db.session.commit()
    flash("You're registered. Event details are available from your dashboard.", "success")
    return redirect(url_for("dashboard"))


@app.route("/account/create", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        if not name or "@" not in email or len(password) < 10:
            flash("Enter your name, a valid email, and a password with at least 10 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account already exists for that email. Sign in instead.", "error")
        else:
            user = User(full_name=name, email=email, phone=phone, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            flash("Welcome to your Opportunity Hub account.", "success")
            return redirect(safe_next(request.args.get("next")) or url_for("dashboard"))
    return render_template("account.html", mode="create")


@app.route("/account/sign-in", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            session["user_id"] = user.id
            return redirect(safe_next(request.form.get("next")) or url_for("dashboard"))
        flash("Email or password was not recognized.", "error")
    return render_template("account.html", mode="login", next=request.args.get("next", ""))


@app.post("/account/sign-out")
def logout():
    session.pop("user_id", None)
    flash("You are signed out.", "success")
    return redirect(url_for("home"))


@app.get("/my-hub")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login", next=url_for("dashboard")))
    user = db.session.get(User, session["user_id"]) or abort(404)
    applications = Application.query.filter_by(user_id=user.id).order_by(Application.created_at.desc()).all()
    registrations = EventRegistration.query.filter_by(user_id=user.id).order_by(EventRegistration.created_at.desc()).all()
    saved = SavedOpportunity.query.filter_by(user_id=user.id).all()
    return render_template("dashboard.html", user=user, applications=applications, registrations=registrations, saved=saved)


def safe_next(value: str | None) -> str | None:
    if not value or not value.startswith("/") or value.startswith("//"):
        return None
    parsed = urlparse(value)
    if parsed.netloc or parsed.scheme:
        return None
    return value


@app.get("/payments/<reference>")
def payment(reference):
    record = Payment.query.filter_by(reference=reference).first_or_404()
    if not session.get("admin") and not payment_belongs_to_user(record, session.get("user_id")):
        abort(403)
    return render_template("payment.html", payment=record, demo=os.getenv("DEMO_PAYMENTS", "false").lower() == "true", configured=bool(os.getenv("FLW_SECRET_KEY", "").strip()), methods=PAYMENT_OPTIONS)


def payment_belongs_to_user(record: Payment, user_id: int | None) -> bool:
    if not user_id:
        return False
    if record.owner_type == "application":
        owner = db.session.get(Application, record.owner_id)
    else:
        owner = db.session.get(EventRegistration, record.owner_id)
    return bool(owner and owner.user_id == user_id)


@app.post("/payments/<reference>/checkout")
def payment_checkout(reference):
    record = Payment.query.filter_by(reference=reference).first_or_404()
    if not session.get("admin") and not payment_belongs_to_user(record, session.get("user_id")):
        abort(403)
    if record.status == "paid":
        flash("This payment has already been confirmed.", "success")
        return redirect(url_for("dashboard"))
    if os.getenv("DEMO_PAYMENTS", "false").lower() == "true":
        return redirect(url_for("payment_demo_complete", reference=reference))
    secret = os.getenv("FLW_SECRET_KEY", "").strip()
    if not secret:
        flash("Payments are not configured yet. This preview will not accept real money.", "error")
        return redirect(url_for("payment", reference=reference))
    owner = db.session.get(Application if record.owner_type == "application" else EventRegistration, record.owner_id)
    user = db.session.get(User, owner.user_id)
    payload = {"tx_ref": record.reference, "amount": record.amount_tzs, "currency": record.currency, "redirect_url": url_for("payment_callback", _external=True), "payment_options": PAYMENT_OPTIONS, "customer": {"email": user.email, "name": user.full_name, "phonenumber": user.phone}, "customizations": {"title": "Opportunity Hub", "description": "Secure program or event payment"}, "meta": {"payment_reference": record.reference}}
    try:
        response = requests.post("https://api.flutterwave.com/v3/payments", json=payload, headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}, timeout=20)
        response.raise_for_status()
        checkout_url = response.json().get("data", {}).get("link", "")
        if not checkout_url.startswith("https://checkout.flutterwave.com/"):
            raise ValueError("Gateway response did not include a valid checkout page")
        return redirect(checkout_url)
    except (requests.RequestException, ValueError):
        app.logger.exception("Unable to start Flutterwave checkout for %s", record.reference)
        flash("Secure checkout could not start. Try again or contact the Opportunity Hub team.", "error")
        return redirect(url_for("payment", reference=reference))


def verify_gateway_payment(transaction_id: str, record: Payment) -> bool:
    secret = os.getenv("FLW_SECRET_KEY", "").strip()
    if not secret or not transaction_id.isdigit():
        return False
    response = requests.get(f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify", headers={"Authorization": f"Bearer {secret}"}, timeout=20)
    response.raise_for_status()
    data = response.json().get("data", {})
    return data.get("status") == "successful" and data.get("tx_ref") == record.reference and data.get("currency") == record.currency and Decimal(str(data.get("amount", 0))) >= Decimal(record.amount_tzs)


def mark_payment_paid(record: Payment, transaction_id: str):
    record.status = "paid"
    record.gateway_transaction_id = transaction_id
    if record.owner_type == "application":
        db.session.get(Application, record.owner_id).payment_status = "paid"
    else:
        db.session.get(EventRegistration, record.owner_id).payment_status = "paid"
    db.session.commit()


@app.get("/payments/callback")
def payment_callback():
    record = Payment.query.filter_by(reference=request.args.get("tx_ref", "")).first_or_404()
    if request.args.get("status") == "successful" and request.args.get("transaction_id"):
        try:
            if verify_gateway_payment(request.args["transaction_id"], record):
                mark_payment_paid(record, request.args["transaction_id"])
                flash("Payment confirmed. Your dashboard is up to date.", "success")
                return redirect(url_for("dashboard"))
        except requests.RequestException:
            app.logger.exception("Payment verification unavailable for %s", record.reference)
    flash("Payment is not confirmed yet. Check the status again in your dashboard.", "info")
    return redirect(url_for("dashboard"))


@app.post("/payments/<reference>/demo-complete")
def payment_demo_complete(reference):
    if os.getenv("DEMO_PAYMENTS", "false").lower() != "true":
        abort(404)
    record = Payment.query.filter_by(reference=reference).first_or_404()
    if not session.get("admin") and not payment_belongs_to_user(record, session.get("user_id")):
        abort(403)
    mark_payment_paid(record, f"DEMO-{record.reference}")
    flash("Demo payment recorded. No real money was charged.", "success")
    return redirect(url_for("dashboard"))


@app.post("/webhooks/flutterwave")
@csrf.exempt
def flutterwave_webhook():
    key = os.getenv("FLW_WEBHOOK_SECRET_HASH", "").strip()
    if not key or not secrets.compare_digest(request.headers.get("verif-hash", ""), key):
        abort(401)
    payload = request.get_json(silent=True) or {}
    if payload.get("event") != "charge.completed":
        return "", 200
    data = payload.get("data", {})
    record = Payment.query.filter_by(reference=data.get("tx_ref", "")).first()
    if not record or not data.get("id"):
        return "", 200
    try:
        if verify_gateway_payment(str(data["id"]), record):
            mark_payment_paid(record, str(data["id"]))
    except requests.RequestException:
        db.session.rollback()
        app.logger.exception("Payment webhook verification unavailable")
        return "verification unavailable", 503
    return "", 200


def require_admin():
    if not session.get("admin"):
        abort(403)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin"):
        if request.method == "POST" and request.form.get("password") == os.getenv("ADMIN_PASSWORD", ""):
            session["admin"] = True
            return redirect(url_for("admin"))
        if request.method == "POST":
            flash("Admin password did not match.", "error")
        return render_template("admin_login.html")
    opportunities = Opportunity.query.order_by(Opportunity.created_at.desc()).all()
    events = Event.query.order_by(Event.created_at.desc()).all()
    return render_template("admin.html", opportunities=opportunities, events=events, media_items=MediaItem.query.order_by(MediaItem.created_at.desc()).all(), pages={page: PageSection.query.filter_by(page=page).all() for page in PAGES}, page_media={page: ContentMedia.query.filter_by(content_type="page", content_key=page).order_by(ContentMedia.id).all() for page in PAGES}, opportunity_media={item.id: content_media_for("opportunity", item.id) for item in opportunities}, event_media={item.id: content_media_for("event", item.id) for item in events}, applications=Application.query.order_by(Application.created_at.desc()).limit(30).all(), registrations=EventRegistration.query.order_by(EventRegistration.created_at.desc()).limit(30).all(), subscribers=Subscriber.query.order_by(Subscriber.created_at.desc()).all(), messages=ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(30).all(), payments=Payment.query.order_by(Payment.created_at.desc()).limit(30).all())


@app.post("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


@app.post("/admin/media")
def admin_add_media():
    require_admin()
    upload = request.files.get("media_file")
    clean_name = secure_filename(upload.filename or "") if upload else ""
    extension = Path(clean_name).suffix.lower()
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    video_extensions = {".mp4", ".webm", ".mov"}
    if not upload or not clean_name or extension not in image_extensions | video_extensions:
        flash("Choose a JPG, PNG, WebP, GIF, MP4, WebM or MOV file.", "error")
        return redirect(url_for("admin") + "#manage-media")
    media_type = "photo" if extension in image_extensions else "video"
    relative_dir = Path("uploads") / "media"
    upload_dir = Path(app.static_folder) / relative_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{secrets.token_hex(16)}{extension}"
    upload.save(upload_dir / stored_name)
    item = MediaItem(
        title=request.form.get("title", "").strip()[:180] or Path(clean_name).stem[:180],
        caption=request.form.get("caption", "").strip()[:500],
        media_type=media_type,
        file_path=(relative_dir / stored_name).as_posix(),
        show_on_home=request.form.get("show_on_home") == "on",
        show_in_gallery=request.form.get("show_in_gallery") == "on",
    )
    db.session.add(item)
    db.session.commit()
    flash("Photo or video added to the media library.", "success")
    return redirect(url_for("admin") + "#manage-media")


@app.post("/admin/media/<int:media_id>")
def admin_update_media(media_id):
    require_admin()
    item = db.session.get(MediaItem, media_id) or abort(404)
    action = request.form.get("action")
    if action == "homepage":
        item.show_on_home = not item.show_on_home
    elif action == "gallery":
        item.show_in_gallery = not item.show_in_gallery
    elif action == "delete":
        upload_root = (Path(app.static_folder) / "uploads" / "media").resolve()
        file_path = (Path(app.static_folder) / item.file_path).resolve()
        if file_path.parent == upload_root and file_path.is_file():
            file_path.unlink()
        ContentMedia.query.filter_by(media_id=item.id).delete(synchronize_session=False)
        db.session.delete(item)
        db.session.commit()
        flash("Media item deleted.", "success")
        return redirect(url_for("admin") + "#manage-media")
    else:
        abort(400)
    db.session.commit()
    flash("Media visibility updated.", "success")
    return redirect(url_for("admin") + "#manage-media")


@app.post("/admin/opportunities")
def admin_add_opportunity():
    require_admin()
    form = request.form
    uploads = request.files.getlist("content_media")
    if not content_uploads_are_valid(uploads):
        return redirect(url_for("admin") + "#manage-opportunities")
    title, summary, description = (form.get(key, "").strip() for key in ("title", "summary", "description"))
    category = form.get("category", "")
    try:
        fee = max(0, int(form.get("fee_amount", "0") or 0))
    except ValueError:
        fee = -1
    if not title or not summary or not description or category not in CATEGORIES or fee < 0:
        flash("Complete the listing fields and enter a valid fee amount.", "error")
    else:
        item = Opportunity(slug=slugify(title), title=title, category=category, location=form.get("location", "Worldwide · Online").strip() or "Worldwide · Online", level=form.get("level", "All levels").strip() or "All levels", deadline=form.get("deadline", "Open until filled").strip() or "Open until filled", summary=summary, description=description, eligibility=form.get("eligibility", "Details shared below.").strip(), benefits=form.get("benefits", "").strip(), application_fee_tzs=fee, featured=form.get("featured") == "on")
        db.session.add(item)
        db.session.flush()
        attach_content_uploads(uploads, "opportunity", item.id, form.get("media_caption", ""))
        db.session.commit()
        send_member_alert(f"New opportunity: {item.title}", f"{item.summary}\n\nFind this opportunity in your personal Opportunity Hub.")
        flash("Opportunity published on Opportunity Hub.", "success")
    return redirect(url_for("admin") + "#manage-opportunities")


@app.post("/admin/events")
def admin_add_event():
    require_admin()
    form = request.form
    uploads = request.files.getlist("content_media")
    if not content_uploads_are_valid(uploads):
        return redirect(url_for("admin") + "#manage-events")
    title, summary, start_at = (form.get(key, "").strip() for key in ("title", "summary", "start_at"))
    try:
        capacity, fee = int(form.get("capacity", "100")), int(form.get("fee_amount", "0"))
    except ValueError:
        capacity, fee = 0, -1
    if not title or not summary or not start_at or capacity < 1 or fee < 0:
        flash("Enter an event title, summary, date, valid capacity and fee.", "error")
    else:
        location = form.get("location", "Worldwide · Online").strip() or "Worldwide · Online"
        event = Event(slug=slugify(title), title=title, event_type=form.get("event_type", "Community event").strip() or "Community event", start_at=start_at, end_at=form.get("end_at", "").strip(), location=location, summary=summary, description=form.get("description", "").strip(), capacity=capacity, ticket_price_tzs=fee)
        db.session.add(event)
        db.session.flush()
        attach_content_uploads(uploads, "event", event.id, form.get("media_caption", ""))
        db.session.commit()
        send_member_alert(f"New Opportunity Hub event: {title}", f"{summary}\n\nDate: {start_at}\nLocation: {location}\n\nFind and register for this event in your personal Opportunity Hub.")
        flash("Event published on the Opportunity Hub calendar.", "success")
    return redirect(url_for("admin") + "#manage-events")


@app.post("/admin/pages/<page>")
def admin_update_page(page):
    require_admin()
    if page not in PAGES:
        abort(404)
    uploads = request.files.getlist("content_media")
    if not content_uploads_are_valid(uploads):
        return redirect(url_for("admin") + f"#page-{page}")
    for section in PageSection.query.filter_by(page=page).all():
        section.value = request.form.get(section.section_key, section.value).strip()[:4000]
    attach_content_uploads(uploads, "page", page, request.form.get("media_caption", ""))
    db.session.commit()
    flash(f"{PAGES[page]} content saved. Any attached media will appear on that page.", "success")
    return redirect(url_for("admin") + f"#page-{page}")


@app.post("/admin/content-media/<int:link_id>/delete")
def admin_delete_content_media(link_id):
    require_admin()
    link = db.session.get(ContentMedia, link_id) or abort(404)
    media = link.media
    upload_root = (Path(app.static_folder) / "uploads" / "media").resolve()
    file_path = (Path(app.static_folder) / media.file_path).resolve() if media else None
    db.session.delete(link)
    if media:
        remaining_links = ContentMedia.query.filter(ContentMedia.media_id == media.id, ContentMedia.id != link.id).count()
        if not remaining_links:
            if file_path and file_path.parent == upload_root and file_path.is_file():
                file_path.unlink()
            db.session.delete(media)
    db.session.commit()
    flash("Attached photo or video removed from this content.", "success")
    if link.content_type == "page":
        return redirect(url_for("admin") + f"#page-{link.content_key}")
    section = "opportunities" if link.content_type == "opportunity" else "events"
    return redirect(url_for("admin") + f"#manage-{section}")


@app.post("/admin/toggle/<kind>/<int:record_id>")
def admin_toggle(kind, record_id):
    require_admin()
    model = Opportunity if kind == "opportunity" else Event if kind == "event" else None
    if model is None:
        abort(404)
    record = db.session.get(model, record_id) or abort(404)
    record.active = not record.active
    db.session.commit()
    return redirect(url_for("admin") + f"#manage-{kind}s")


@app.post("/admin/applications/<int:application_id>/status")
def admin_update_application_status(application_id):
    require_admin()
    record = db.session.get(Application, application_id) or abort(404)
    status = request.form.get("status", "")
    if status not in {"Submitted", "In review", "Shortlisted", "Offer made", "Not selected"}:
        abort(400)
    record.status = status
    db.session.commit()
    flash("Application status updated.", "success")
    return redirect(url_for("admin") + "#applications")


@app.get("/health")
def health():
    return {"status": "ok"}


with app.app_context():
    db.create_all()
    seed_data()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")

