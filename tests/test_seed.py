"""Seed idempotency: running twice leaves identical row counts."""
from __future__ import annotations

from sqlalchemy import func, select

from app import models


def _counts(session_factory):
    session = session_factory()
    try:
        return {
            "profile": session.scalar(select(func.count()).select_from(models.Profile)),
            "skill": session.scalar(select(func.count()).select_from(models.Skill)),
            "experience": session.scalar(select(func.count()).select_from(models.Experience)),
            "education": session.scalar(select(func.count()).select_from(models.Education)),
            "certificate": session.scalar(select(func.count()).select_from(models.Certificate)),
            "project": session.scalar(select(func.count()).select_from(models.Project)),
            "project_image": session.scalar(select(func.count()).select_from(models.ProjectImage)),
            "social_link": session.scalar(select(func.count()).select_from(models.SocialLink)),
            "testimonial": session.scalar(select(func.count()).select_from(models.Testimonial)),
            "contact_message": session.scalar(select(func.count()).select_from(models.ContactMessage)),
        }
    finally:
        session.close()


def test_seed_is_idempotent(session_factory):
    from app.seed import seed

    seed(session_factory())
    before = _counts(session_factory)

    seed(session_factory())
    after = _counts(session_factory)

    assert before == after
    assert before["testimonial"] == 0
    assert before["project_image"] == 0
    assert before["contact_message"] == 0
