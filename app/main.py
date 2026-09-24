"""FastAPI application: routes, middleware, static mounts and admin."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.admin import setup_admin, verify_basic_auth
from app.config import (
    CF_ANALYTICS_TOKEN,
    EMAIL_FROM,
    EMAIL_TO,
    SITE_URL,
    UPLOAD_DIR,
)
from app.db import Base, engine, get_db
from app.email import send_contact_email
from app.i18n import _current_lang, get_lang, pick_localized, t, pick, translate
from app.models import (
    Certificate,
    ContactMessage,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
    SocialLink,
    Testimonial,
)
from app.schemas import ContactForm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Rate limit store: client IP -> list of recent submission timestamps (3/hour).
RATE_LIMITS: dict[str, list[float]] = {}

_AR_MONTHS = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]


# --------------------------------------------------------------------------- #
# Jinja globals
# --------------------------------------------------------------------------- #
def asset_url(value: Any) -> str:
    """Turn a stored filename into a /uploads/ URL (or pass absolute URLs through)."""
    if not value:
        return ""
    value = str(value)
    if value.startswith(("http://", "https://", "/", "data:")):
        return value
    return "/uploads/" + value.lstrip("/")


def project_url(slug: str) -> str:
    """Language-aware URL for a project detail page."""
    prefix = "/ar" if _current_lang.get() == "ar" else ""
    return f"{prefix}/projects/{slug}"


def format_date(value: Any, lang: str | None = None) -> str:
    """Render a date as 'Feb 2026' (English) or 'فبراير 2026' (Arabic)."""
    if value is None:
        return ""
    lang = lang or _current_lang.get()
    if lang == "ar":
        return f"{_AR_MONTHS[value.month - 1]} {value.year}"
    return value.strftime("%b %Y")


templates.env.globals["t"] = t
templates.env.globals["pick"] = pick
templates.env.globals["asset_url"] = asset_url
templates.env.globals["project_url"] = project_url
templates.env.globals["format_date"] = format_date


# --------------------------------------------------------------------------- #
# URL helpers
# --------------------------------------------------------------------------- #
def _lang_paths(path: str) -> tuple[str, str]:
    """Return (english_path, arabic_path) for a given path."""
    if path == "/ar":
        return "/", "/ar"
    if path.startswith("/ar/"):
        return path[3:], path
    if path == "/":
        return "/", "/ar"
    return path, "/ar" + path


def _home_path(lang: str) -> str:
    return "/ar" if lang == "ar" else "/"


def _absolute_asset(value: Any) -> str:
    """Return an absolute URL for a stored upload (or pass full URLs through)."""
    url = asset_url(value)
    if url.startswith(("http://", "https://")):
        return url
    return SITE_URL + url


def _og_image(profile: Profile | None) -> str:
    if profile and profile.og_image_url:
        return _absolute_asset(profile.og_image_url)
    if profile and profile.avatar_url:
        return _absolute_asset(profile.avatar_url)
    return SITE_URL + "/static/img/og.png"


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render(request: Request, template_name: str, context: dict | None = None,
           status_code: int = 200, headers: dict | None = None) -> Response:
    lang = get_lang(request)
    token = _current_lang.set(lang)
    try:
        ctx = dict(context or {})
        ctx.setdefault("lang", lang)
        ctx.setdefault("home_path", _home_path(lang))
        ctx.setdefault("contact_action", "/ar/contact" if lang == "ar" else "/contact")
        ctx.setdefault("site_name", "Mohammed Alhariri")
        ctx.setdefault("cf_analytics_token", CF_ANALYTICS_TOKEN)
        ctx.setdefault("title", translate("meta.title", lang))
        ctx.setdefault("meta_description", translate("meta.description", lang))
        en_path, ar_path = _lang_paths(request.url.path)
        ctx.setdefault("canonical", SITE_URL + request.url.path)
        ctx.setdefault("alternate_en", SITE_URL + en_path)
        ctx.setdefault("alternate_ar", SITE_URL + ar_path)
        ctx.setdefault("switch_url", ar_path if lang == "en" else en_path)
        ctx.setdefault("og_type", "website")
        ctx.setdefault("og_image", SITE_URL + "/static/img/og.png")
        return templates.TemplateResponse(
            request, template_name, ctx, status_code=status_code, headers=headers
        )
    finally:
        _current_lang.reset(token)


# --------------------------------------------------------------------------- #
# Data helpers
# --------------------------------------------------------------------------- #
def _group_skills(skills: list[Skill]) -> dict[str, list[Skill]]:
    groups: dict[str, list[Skill]] = {}
    for skill in skills:
        groups.setdefault(skill.category or "", []).append(skill)
    return groups


def _home_context(db: Session, lang: str, form_errors: dict | None = None,
                  form_data: dict | None = None) -> dict:
    profile = db.get(Profile, 1)
    skills = db.scalars(
        select(Skill).order_by(Skill.sort_order, Skill.name_en)
    ).all()
    experiences = db.scalars(
        select(Experience).order_by(Experience.sort_order, Experience.start_date.desc())
    ).all()
    education = db.scalars(
        select(Education).order_by(Education.start_date.desc())
    ).all()
    certificates = db.scalars(
        select(Certificate).order_by(Certificate.issue_date.desc())
    ).all()
    projects = db.scalars(
        select(Project)
        .options(selectinload(Project.images), selectinload(Project.skills))
        .order_by(Project.featured.desc(), Project.sort_order, Project.title_en)
    ).unique().all()
    testimonials = db.scalars(
        select(Testimonial).where(Testimonial.published.is_(True))
    ).all()
    socials = db.scalars(select(SocialLink).order_by(SocialLink.sort_order)).all()

    if profile is not None:
        title = f"{profile.ar_name} — {pick_localized(profile, 'title', lang)}"
        meta_description = pick_localized(profile, "tagline", lang) or translate("meta.description", lang)
    else:
        title = translate("meta.title", lang)
        meta_description = translate("meta.description", lang)

    person = {
        "@type": "Person",
        "name": profile.name_en if profile else "Mohammed Alhariri",
        "jobTitle": pick_localized(profile, "title", lang),
        "email": profile.email if profile and profile.email else "",
        "url": SITE_URL,
        "sameAs": [profile.github_url] if profile and profile.github_url else [],
    }
    website = {"@type": "WebSite", "name": "Mohammed Alhariri", "url": SITE_URL}
    jsonld = {"@context": "https://schema.org", "@graph": [person, website]}

    return {
        "profile": profile,
        "skills_by_category": _group_skills(skills),
        "experiences": experiences,
        "education": education,
        "certificates": certificates,
        "projects": projects,
        "testimonials": testimonials,
        "socials": socials,
        "sent": False,
        "form_errors": form_errors or {},
        "form_data": form_data or {},
        "loaded_at": int(time.time()),
        "title": title,
        "meta_description": meta_description,
        "og_image": _og_image(profile),
        "jsonld": jsonld,
    }


# --------------------------------------------------------------------------- #
# Contact helpers
# --------------------------------------------------------------------------- #
def _format_errors(exc: ValidationError) -> dict[str, str]:
    errors: dict[str, str] = {}
    for err in exc.errors():
        field = ".".join(str(part) for part in err["loc"])
        if field in errors:
            continue
        errors[field] = f"contact.error.{field}"
    return errors


def _parse_loaded_at(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _save_contact(db: Session, form: ContactForm, *, is_spam: bool) -> ContactMessage:
    message = ContactMessage(
        name=form.name,
        email=form.email,
        subject=form.subject,
        body=form.message,
        created_at=datetime.now(timezone.utc),
        is_spam=is_spam,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


# --------------------------------------------------------------------------- #
# Lifespan and app
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Mohammed Alhariri Portfolio", lifespan=lifespan)


@app.middleware("http")
async def app_middleware(request: Request, call_next):
    if request.url.path.startswith("/admin") and not verify_basic_auth(request):
        return Response(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": "Basic realm=portfolio-admin"},
        )

    token = _current_lang.set(get_lang(request))
    try:
        response = await call_next(request)
    finally:
        _current_lang.reset(token)

    if request.url.path.startswith(("/static", "/uploads")):
        response.headers["Cache-Control"] = "public, max-age=2592000"
    else:
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return render(request, "errors/404.html", status_code=404)
    if exc.status_code == 429:
        return render(request, "errors/429.html", status_code=429)
    return Response(status_code=exc.status_code)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/")
@app.get("/ar")
def home(request: Request, db: Session = Depends(get_db)):
    lang = get_lang(request)
    context = _home_context(db, lang)
    context["sent"] = request.query_params.get("sent") == "1"
    return render(request, "index.html", context)


@app.get("/projects/{slug}")
@app.get("/ar/projects/{slug}")
def project_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    lang = get_lang(request)
    project = db.scalar(
        select(Project)
        .where(Project.slug == slug)
        .options(selectinload(Project.images), selectinload(Project.skills))
    )
    if project is None:
        raise HTTPException(status_code=404)

    profile = db.get(Profile, 1)
    title = f"{pick_localized(project, 'title', lang)} — {profile.name if profile else ''}".rstrip(" —")
    meta_description = pick_localized(project, "summary", lang)
    og_image = _og_image(profile)
    if project.images:
        og_image = _absolute_asset(project.images[0].url)

    return render(request, "project_detail.html", {
        "project": project,
        "profile": profile,
        "title": title,
        "meta_description": meta_description,
        "og_image": og_image,
        "og_type": "article",
    })


@app.post("/contact")
@app.post("/ar/contact")
async def contact(request: Request, db: Session = Depends(get_db)):
    lang = get_lang(request)
    form = await request.form()
    data = {key: value for key, value in form.items() if isinstance(value, str)}

    try:
        contact_form = ContactForm(**data)
    except ValidationError as exc:
        errors = _format_errors(exc)
        context = _home_context(db, lang, form_errors=errors, form_data=data)
        return render(request, "index.html", context)

    # 2. Honeypot -> record as spam, fake success, no email.
    if contact_form.website.strip():
        _save_contact(db, contact_form, is_spam=True)
        return RedirectResponse(f"{_home_path(lang)}?sent=1", status_code=303)

    # 3. Time-gate -> submitted before 2s elapsed is spam.
    loaded_at = _parse_loaded_at(contact_form.loaded_at)
    if loaded_at is None or (time.time() - loaded_at) < 2:
        _save_contact(db, contact_form, is_spam=True)
        return RedirectResponse(f"{_home_path(lang)}?sent=1", status_code=303)

    # 4. Rate limit: 3 submissions per hour per IP.
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    timestamps = RATE_LIMITS.setdefault(ip, [])
    timestamps[:] = [ts for ts in timestamps if now - ts < 3600]
    if len(timestamps) >= 3:
        return render(request, "errors/429.html", status_code=429)
    timestamps.append(now)

    # 5. Insert the real message.
    message = _save_contact(db, contact_form, is_spam=False)

    # 6. Send via Resend; failures are logged and the row is kept.
    subject_line = f"Portfolio contact: {contact_form.subject}" if contact_form.subject else "Portfolio contact"
    body = (
        f"Name: {contact_form.name}\n"
        f"Email: {contact_form.email}\n"
        f"Subject: {contact_form.subject or '-'}\n\n"
        f"{contact_form.message}"
    )
    try:
        send_contact_email(
            to=EMAIL_TO,
            from_=EMAIL_FROM,
            reply_to=contact_form.email,
            subject=subject_line,
            text=body,
        )
    except Exception:
        logger.exception("Failed to send contact email for message id=%s", message.id)

    # 7. Redirect with a confirmation query param.
    return RedirectResponse(f"{_home_path(lang)}?sent=1", status_code=303)


@app.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    slugs = db.scalars(select(Project.slug)).all()
    urls = [SITE_URL + "/", SITE_URL + "/ar"]
    urls.extend(SITE_URL + f"/projects/{slug}" for slug in slugs)
    urls.extend(SITE_URL + f"/ar/projects/{slug}" for slug in slugs)
    body = ['<?xml version="1.0" encoding="UTF-8"?>']
    body.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for url in urls:
        body.append(f"  <url><loc>{url}</loc></url>")
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")


@app.get("/robots.txt")
def robots():
    body = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    return Response(body, media_type="text/plain")


@app.get("/healthz")
def healthz():
    return Response("ok", media_type="text/plain")


# --------------------------------------------------------------------------- #
# Admin + static mounts
# --------------------------------------------------------------------------- #
setup_admin(app)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
