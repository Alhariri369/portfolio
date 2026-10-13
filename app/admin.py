"""SQLAdmin setup and HTTP Basic Auth guard for /admin.

Uploads go to Cloudflare R2 via app.storage; the resulting public URL is
stored in the (String) model column, so the public site renders it directly.
"""

from __future__ import annotations

import base64
import re
import secrets
import uuid
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect
from sqladmin.fields import FileField
from sqladmin import Admin, BaseView, ModelView, expose
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.config import ADMIN_PASSWORD, ADMIN_USERNAME
from app.db import SessionLocal, engine
from app.models import (
    Certificate,
    ContactMessage,
    Education,
    Experience,
    Profile,
    Project,
    ProjectImage,
    Skill,
    SocialLink,
    Testimonial,
)
from app.storage import upload_fileobj


def _all_columns(model) -> list[str]:
    return [c.key for c in sa_inspect(model).mapper.column_attrs]

class ExportMixin:
    can_export = True
    export_types = ["json"]          # use ["json", "csv"] if you want both

    def __init__(self):
        # must be set before ModelView.__init__ builds its export column list
        self.column_export_list = _all_columns(self.model)
        super().__init__()

# Sentinel meaning "clear this file" (produced by the clear checkbox widget).
_CLEAR = "__sqladmin_clear__"


def verify_basic_auth(request) -> bool:
    """Check the Authorization header with constant-time comparison."""
    header = request.headers.get("authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:]).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        return False
    return secrets.compare_digest(username, ADMIN_USERNAME) and secrets.compare_digest(
        password, ADMIN_PASSWORD
    )


def _safe_filename(filename: str) -> str:
    name = Path(filename or "upload").name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._") or "upload"
    return name


class R2FileField(FileField):
    """A FileField that uploads to Cloudflare R2 and stores the public URL."""

    def process_formdata(self, valuelist):
        if not valuelist:
            self.data = None
            return

        value = valuelist[0]

        # Untouched file input: browser submits an empty string.
        if isinstance(value, str):
            self.data = value or None
            return

        filename = getattr(value, "filename", None)
        if not filename:
            # Clear checkbox produced an empty upload.
            self.data = _CLEAR
            return

        fileobj = getattr(value, "file", None) or getattr(value, "stream", None)
        if fileobj is None:
            self.data = None
            return

        content_type = (
            getattr(value, "content_type", None) or "application/octet-stream"
        )
        safe = _safe_filename(filename)
        key = f"uploads/{uuid.uuid4().hex[:12]}-{safe}"

        fileobj.seek(0)
        url = upload_fileobj(fileobj, key, content_type=content_type)
        self.data = url


class FileUploadMixin:
    """Restores untouched upload fields on edit and honours explicit clears."""

    file_columns: tuple[str, ...] = ()

    async def on_model_change(self, data, model, is_created, request):
        form = await request.form()
        for column in self.file_columns:
            value = data.get(column)
            should_clear = bool(form.get(f"{column}_checkbox")) or value == _CLEAR
            if should_clear:
                data[column] = None
            elif not is_created and (value is None or value == ""):
                data[column] = getattr(model, column, None)
        await super().on_model_change(data, model, is_created, request)


class ProfileAdmin(ExportMixin, FileUploadMixin, ModelView, model=Profile):
    file_columns = ("avatar_url", "banner_url", "resume_pdf_url", "og_image_url")
    column_list = ["id", "name_en", "title_en", "email", "phone"]
    form_columns = [
        "name_en",
        "name_ar",
        "title_en",
        "title_ar",
        "tagline_en",
        "tagline_ar",
        "summary_en",
        "summary_ar",
        "location_en",
        "location_ar",
        "email",
        "phone",
        "github_url",
        "avatar_url",
        "banner_url",
        "resume_pdf_url",
        "og_image_url",
    ]
    form_overrides = {
        "avatar_url": R2FileField,
        "banner_url": R2FileField,
        "resume_pdf_url": R2FileField,
        "og_image_url": R2FileField,
    }


class SkillAdmin(ExportMixin, ModelView, model=Skill):
    column_list = ["id", "name_en", "name_ar", "category", "sort_order"]
    form_columns = ["name_en", "name_ar", "category", "sort_order"]


class ExperienceAdmin(ExportMixin, ModelView, model=Experience):
    column_list = [
        "id",
        "role_en",
        "company_en",
        "start_date",
        "end_date",
        "sort_order",
    ]
    form_columns = [
        "company_en",
        "company_ar",
        "role_en",
        "role_ar",
        "location_en",
        "location_ar",
        "start_date",
        "end_date",
        "is_current",
        "description_en",
        "description_ar",
        "sort_order",
    ]


class EducationAdmin(ExportMixin, ModelView, model=Education):
    column_list = ["id", "degree_en", "institution_en", "start_date", "end_date"]
    form_columns = [
        "institution_en",
        "institution_ar",
        "degree_en",
        "degree_ar",
        "field_en",
        "field_ar",
        "start_date",
        "end_date",
        "description_en",
        "description_ar",
    ]


class CertificateAdmin(ExportMixin, ModelView, model=Certificate):
    column_list = ["id", "name_en", "issuer_en", "issue_date"]
    form_columns = ["name_en", "name_ar", "issuer_en", "issuer_ar", "issue_date", "url"]


class ProjectAdmin(ExportMixin, ModelView, model=Project):
    column_list = ["id", "slug", "title_en", "featured", "sort_order"]
    form_columns = [
        "slug",
        "title_en",
        "title_ar",
        "summary_en",
        "summary_ar",
        "description_en",
        "description_ar",
        "repo_url",
        "live_url",
        "featured",
        "sort_order",
        "skills",
    ]


class ProjectImageAdmin(ExportMixin, FileUploadMixin, ModelView, model=ProjectImage):
    file_columns = ("url",)
    column_list = ["id", "project_id", "url", "sort_order"]
    form_columns = ["project", "url", "alt_en", "alt_ar", "sort_order"]
    form_overrides = {"url": R2FileField}


class SocialLinkAdmin(ExportMixin, ModelView, model=SocialLink):
    column_list = ["id", "platform", "url", "sort_order"]
    form_columns = ["platform", "url", "sort_order"]


class TestimonialAdmin(ExportMixin, ModelView, model=Testimonial):
    column_list = ["id", "author_en", "role_en", "published"]
    form_columns = [
        "author_en",
        "author_ar",
        "role_en",
        "role_ar",
        "text_en",
        "text_ar",
        "published",
    ]


class ContactMessageAdmin(ExportMixin, ModelView, model=ContactMessage):
    column_list = ["id", "created_at", "name", "email", "subject", "is_spam"]
    column_searchable_list = ["name", "email", "subject"]
    column_sortable_list = ["created_at", "is_spam"]
    can_create = False
    can_edit = False
    can_delete = True
    
    
# Export dashboard and export everything
# Start export helpers 
EXPORT_MODELS = {
    "profile": Profile, "skills": Skill, "experience": Experience,
    "education": Education, "certificates": Certificate,
    "projects": Project, "project_images": ProjectImage,
    "social_links": SocialLink, "testimonials": Testimonial,
    "contact_messages": ContactMessage,
}

def _json_download(payload: dict, filename: str) -> JSONResponse:
    return JSONResponse(
        jsonable_encoder(payload),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
# End export helpers 
""" old
class DashboardView(BaseView):
    name = "Dashboard"
    icon = "fa-solid fa-chart-line"

    @expose("/dashboard", methods=["GET"])
    async def dashboard(self, request):
        since = datetime.now(timezone.utc) - timedelta(days=13)
        with SessionLocal() as s:
            def count(model, *where):
                return s.scalar(select(func.count()).select_from(model).where(*where))

            stats = {
                "Projects": count(Project),
                "Skills": count(Skill),
                "Certificates": count(Certificate),
                "Messages": count(ContactMessage, ContactMessage.is_spam.is_(False)),
                "Spam blocked": count(ContactMessage, ContactMessage.is_spam.is_(True)),
            }
            latest = s.scalars(
                select(ContactMessage)
                .where(ContactMessage.is_spam.is_(False))
                .order_by(ContactMessage.created_at.desc())
                .limit(5)
            ).all()
            recent = s.scalars(
                select(ContactMessage.created_at)
                .where(ContactMessage.created_at >= since)
            ).all()

        per_day = Counter(d.date() for d in recent)
        days = [(since + timedelta(days=i)).date() for i in range(14)]
        return await self.templates.TemplateResponse(
            request,
            "sqladmin/dashboard.html",
            {
                "stats": stats,
                "latest": latest,
                "labels": [d.strftime("%b %d") for d in days],
                "values": [per_day.get(d, 0) for d in days],
            },
        )
"""

class DashboardView(BaseView):
    name = "Dashboard"
    icon = "fa-solid fa-chart-line"

    def _data(self):
        since = datetime.now(timezone.utc) - timedelta(days=13)
        with SessionLocal() as s:
            def count(model, *where):
                return s.scalar(select(func.count()).select_from(model).where(*where))

            stats = {
                "Projects": count(Project),
                "Skills": count(Skill),
                "Certificates": count(Certificate),
                "Messages": count(ContactMessage, ContactMessage.is_spam.is_(False)),
                "Spam blocked": count(ContactMessage, ContactMessage.is_spam.is_(True)),
            }
            latest = s.scalars(
                select(ContactMessage).where(ContactMessage.is_spam.is_(False))
                .order_by(ContactMessage.created_at.desc()).limit(5)
            ).all()
            recent = s.scalars(
                select(ContactMessage.created_at).where(ContactMessage.created_at >= since)
            ).all()
            latest_rows = [
                {"name": m.name, "email": m.email, "subject": m.subject,
                 "created_at": m.created_at} for m in latest
            ]
        per_day = Counter(d.date() for d in recent)
        days = [(since + timedelta(days=i)).date() for i in range(14)]
        return {
            "stats": stats,
            "latest": latest_rows,
            "labels": [d.strftime("%b %d") for d in days],
            "values": [per_day.get(d, 0) for d in days],
        }

    @expose("/dashboard", methods=["GET"])
    async def dashboard(self, request):
        return await self.templates.TemplateResponse(
            request, "sqladmin/dashboard.html", self._data()
        )

    @expose("/dashboard/export", methods=["GET"])
    async def export_dashboard(self, request):
        d = self._data()
        payload = {
            "exported_at": datetime.now(timezone.utc),
            "stats": d["stats"],
            "messages_per_day": dict(zip(d["labels"], d["values"])),
            "latest_messages": d["latest"],
        }
        return _json_download(payload, f"dashboard-{_stamp()}.json")

    @expose("/dashboard/export/full", methods=["GET"])
    async def export_full(self, request):
        payload = {"exported_at": datetime.now(timezone.utc)}
        with SessionLocal() as s:
            for key, model in EXPORT_MODELS.items():
                cols = _all_columns(model)
                rows = s.scalars(select(model).order_by(model.id)).all()
                payload[key] = [{col: getattr(r, col) for col in cols} for r in rows]

                if model is Project:
                    for out, proj in zip(payload[key], rows):
                        out["skills"] = [sk.name_en for sk in proj.skills]
        return _json_download(payload, f"portfolio-full-{_stamp()}.json")


def setup_admin(app) -> Admin:
    """Mount SQLAdmin at /admin and register every model."""
    admin = Admin(app, engine, title="Portfolio Admin", base_url="/admin", templates_dir=str(Path(__file__).resolve().parent / "templates"))
    admin.add_view(DashboardView)   # first = top of sidebar
    admin.add_view(ProfileAdmin)
    admin.add_view(SkillAdmin)
    admin.add_view(ExperienceAdmin)
    admin.add_view(EducationAdmin)
    admin.add_view(CertificateAdmin)
    admin.add_view(ProjectAdmin)
    admin.add_view(ProjectImageAdmin)
    admin.add_view(SocialLinkAdmin)
    admin.add_view(TestimonialAdmin)
    admin.add_view(ContactMessageAdmin)
    return admin