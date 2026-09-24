"""SQLAdmin setup and HTTP Basic Auth guard for /admin.

Uploads are handled by a small custom FileField that writes to UPLOAD_DIR and
stores the resulting filename in the (String) model column, so the public site
serves them through the /uploads static mount.
"""
from __future__ import annotations

import base64
import re
import secrets
import uuid
from pathlib import Path

from sqladmin import Admin, ModelView
from sqladmin.fields import FileField

from app.config import ADMIN_PASSWORD, ADMIN_USERNAME, UPLOAD_DIR
from app.db import engine
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


class LocalFileField(FileField):
    """A FileField that saves uploads locally and stores the filename."""

    def __init__(self, label=None, validators=None, storage=None, **kwargs):
        self.storage = Path(storage) if storage else UPLOAD_DIR
        super().__init__(label, validators, **kwargs)

    def process_formdata(self, valuelist):
        if not valuelist:
            self.data = None
            return

        value = valuelist[0]

        # An empty string means the browser submitted an untouched file input.
        # Return None and let FileUploadMixin restore the existing value.
        if isinstance(value, str):
            self.data = value or None
            return

        filename = getattr(value, "filename", None)
        if not filename:
            # No filename: the "clear" checkbox produced an empty upload.
            self.data = _CLEAR
            return

        fileobj = getattr(value, "file", None) or getattr(value, "stream", None)
        if fileobj is None:
            self.data = None
            return

        safe = _safe_filename(filename)
        unique = f"{Path(safe).stem}-{uuid.uuid4().hex[:8]}{Path(safe).suffix}"
        self.storage.mkdir(parents=True, exist_ok=True)
        fileobj.seek(0)
        (self.storage / unique).write_bytes(fileobj.read())
        self.data = unique


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


class ProfileAdmin(FileUploadMixin, ModelView, model=Profile):
    file_columns = ("avatar_url", "banner_url", "resume_pdf_url", "og_image_url")
    column_list = ["id", "name", "title_en", "email", "phone"]
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
        "avatar_url": LocalFileField,
        "banner_url": LocalFileField,
        "resume_pdf_url": LocalFileField,
        "og_image_url": LocalFileField,
    }
    form_args = {
        "avatar_url": {"storage": str(UPLOAD_DIR)},
        "banner_url": {"storage": str(UPLOAD_DIR)},
        "resume_pdf_url": {"storage": str(UPLOAD_DIR)},
        "og_image_url": {"storage": str(UPLOAD_DIR)},
    }


class SkillAdmin(ModelView, model=Skill):
    column_list = ["id", "name_en", "name_ar", "category", "sort_order"]
    form_columns = ["name_en", "name_ar", "category", "sort_order"]


class ExperienceAdmin(ModelView, model=Experience):
    column_list = ["id", "role_en", "company_en", "start_date", "end_date", "sort_order"]
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


class EducationAdmin(ModelView, model=Education):
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


class CertificateAdmin(ModelView, model=Certificate):
    column_list = ["id", "name_en", "issuer_en", "issue_date"]
    form_columns = ["name_en", "name_ar", "issuer_en", "issuer_ar", "issue_date", "url"]


class ProjectAdmin(ModelView, model=Project):
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


class ProjectImageAdmin(FileUploadMixin, ModelView, model=ProjectImage):
    file_columns = ("url",)
    column_list = ["id", "project_id", "url", "sort_order"]
    form_columns = ["project", "url", "alt_en", "alt_ar", "sort_order"]
    form_overrides = {"url": LocalFileField}
    form_args = {"url": {"storage": str(UPLOAD_DIR)}}


class SocialLinkAdmin(ModelView, model=SocialLink):
    column_list = ["id", "platform", "url", "sort_order"]
    form_columns = ["platform", "url", "sort_order"]


class TestimonialAdmin(ModelView, model=Testimonial):
    column_list = ["id", "author_en", "role_en", "published"]
    form_columns = ["author_en", "author_ar", "role_en", "role_ar", "text_en", "text_ar", "published"]


class ContactMessageAdmin(ModelView, model=ContactMessage):
    column_list = ["id", "created_at", "name", "email", "subject", "is_spam"]
    column_searchable_list = ["name", "email", "subject"]
    column_sortable_list = ["created_at", "is_spam"]
    can_create = False
    can_edit = False
    can_delete = True


def setup_admin(app) -> Admin:
    """Mount SQLAdmin at /admin and register every model."""
    admin = Admin(app, engine, title="Portfolio Admin", base_url="/admin")
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
