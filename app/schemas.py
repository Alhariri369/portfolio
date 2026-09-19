"""Pydantic schemas for form input."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

# Pragmatic email check that avoids an extra dependency (pydantic's EmailStr
# would pull in email-validator). The form has no privileged side effects, so a
# sane RFC-ish shape plus length checks is sufficient.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContactForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=254)
    subject: str = Field(default="", max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    # Anti-spam fields (rendered into the form, never visible to users).
    website: str = Field(default="", max_length=100)
    loaded_at: str = Field(default="")

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("email")
    @classmethod
    def _email_valid(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 254 or not _EMAIL_RE.match(value):
            raise ValueError("invalid email address")
        return value

    @field_validator("subject")
    @classmethod
    def _subject_strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value
