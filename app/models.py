"""SQLAlchemy declarative models (run on both SQLite and Postgres)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow():
    return datetime.now(timezone.utc)


project_skill = Table(
    "project_skill",
    Base.metadata,
    Column("project_id", ForeignKey("project.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", ForeignKey("skill.id", ondelete="CASCADE"), primary_key=True),
)


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_en: Mapped[str] = mapped_column(String(200), default="")
    name_ar: Mapped[str] = mapped_column(String(200), default="")
    title_en: Mapped[str] = mapped_column(String(200), default="")
    title_ar: Mapped[str] = mapped_column(String(200), default="")
    tagline_en: Mapped[str] = mapped_column(String(500), default="")
    tagline_ar: Mapped[str] = mapped_column(String(500), default="")
    summary_en: Mapped[str] = mapped_column(Text, default="")
    summary_ar: Mapped[str] = mapped_column(Text, default="")
    location_en: Mapped[str] = mapped_column(String(200), default="")
    location_ar: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resume_pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    og_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class Skill(Base):
    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_en: Mapped[str] = mapped_column(String(200), default="")
    name_ar: Mapped[str] = mapped_column(String(200), default="")
    category: Mapped[str] = mapped_column(String(200), default="")
    sort_order: Mapped[int] = mapped_column(default=0)

    projects: Mapped[list["Project"]] = relationship(
        secondary=project_skill, back_populates="skills"
    )


class Experience(Base):
    __tablename__ = "experience"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_en: Mapped[str] = mapped_column(String(300), default="")
    company_ar: Mapped[str] = mapped_column(String(300), default="")
    role_en: Mapped[str] = mapped_column(String(300), default="")
    role_ar: Mapped[str] = mapped_column(String(300), default="")
    location_en: Mapped[str] = mapped_column(String(300), default="")
    location_ar: Mapped[str] = mapped_column(String(300), default="")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    description_en: Mapped[str] = mapped_column(Text, default="")
    description_ar: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(default=0)


class Education(Base):
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_en: Mapped[str] = mapped_column(String(300), default="")
    institution_ar: Mapped[str] = mapped_column(String(300), default="")
    degree_en: Mapped[str] = mapped_column(String(300), default="")
    degree_ar: Mapped[str] = mapped_column(String(300), default="")
    field_en: Mapped[str] = mapped_column(String(300), default="")
    field_ar: Mapped[str] = mapped_column(String(300), default="")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    description_en: Mapped[str] = mapped_column(Text, default="")
    description_ar: Mapped[str] = mapped_column(Text, default="")


class Certificate(Base):
    __tablename__ = "certificate"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_en: Mapped[str] = mapped_column(String(300), default="")
    name_ar: Mapped[str] = mapped_column(String(300), default="")
    issuer_en: Mapped[str] = mapped_column(String(300), default="")
    issuer_ar: Mapped[str] = mapped_column(String(300), default="")
    issue_date: Mapped[date] = mapped_column(Date)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class Project(Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title_en: Mapped[str] = mapped_column(String(300), default="")
    title_ar: Mapped[str] = mapped_column(String(300), default="")
    summary_en: Mapped[str] = mapped_column(String(500), default="")
    summary_ar: Mapped[str] = mapped_column(String(500), default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    description_ar: Mapped[str] = mapped_column(Text, default="")
    repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    live_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    images: Mapped[list["ProjectImage"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectImage.sort_order",
    )
    skills: Mapped[list["Skill"]] = relationship(
        secondary=project_skill, back_populates="projects"
    )


class ProjectImage(Base):
    __tablename__ = "project_image"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500), default="")
    alt_en: Mapped[str] = mapped_column(String(300), default="")
    alt_ar: Mapped[str] = mapped_column(String(300), default="")
    sort_order: Mapped[int] = mapped_column(default=0)

    project: Mapped["Project"] = relationship(back_populates="images")


class SocialLink(Base):
    __tablename__ = "social_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(100), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    sort_order: Mapped[int] = mapped_column(default=0)


class Testimonial(Base):
    __tablename__ = "testimonial"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_en: Mapped[str] = mapped_column(String(200), default="")
    author_ar: Mapped[str] = mapped_column(String(200), default="")
    role_en: Mapped[str] = mapped_column(String(300), default="")
    role_ar: Mapped[str] = mapped_column(String(300), default="")
    text_en: Mapped[str] = mapped_column(Text, default="")
    text_ar: Mapped[str] = mapped_column(Text, default="")
    published: Mapped[bool] = mapped_column(Boolean, default=False)


class ContactMessage(Base):
    __tablename__ = "contact_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_spam: Mapped[bool] = mapped_column(Boolean, default=False)
