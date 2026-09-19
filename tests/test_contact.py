"""Contact pipeline tests: validation, spam paths, rate limit, valid submit."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.main import RATE_LIMITS
from app.models import ContactMessage


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    RATE_LIMITS.clear()
    yield
    RATE_LIMITS.clear()


def _form(**overrides):
    data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "subject": "Project inquiry",
        "message": "Hello, I would like to discuss a project with you.",
        "website": "",
        "loaded_at": str(time.time() - 10),
    }
    data.update(overrides)
    return data


def test_validation_rerenders_with_errors(client):
    response = client.post("/contact", data=_form(name=""), follow_redirects=False)
    assert response.status_code == 200
    assert "Please enter your name" in response.text

    response = client.post("/contact", data=_form(email="not-an-email"), follow_redirects=False)
    assert response.status_code == 200
    assert "valid email" in response.text


def test_honeypot_saves_spam_and_sends_no_email(client, session_factory):
    with patch("app.main.send_contact_email") as send:
        response = client.post(
            "/contact", data=_form(website="http://spam.example"), follow_redirects=False
        )

    assert response.status_code == 303
    assert response.headers["location"].endswith("?sent=1")
    send.assert_not_called()

    session = session_factory()
    try:
        count = session.scalar(select(func.count()).select_from(ContactMessage))
        spam = session.scalar(
            select(func.count()).select_from(ContactMessage).where(ContactMessage.is_spam.is_(True))
        )
    finally:
        session.close()
    assert count == 1
    assert spam == 1


def test_time_gate_saves_spam_and_sends_no_email(client, session_factory):
    with patch("app.main.send_contact_email") as send:
        response = client.post(
            "/contact", data=_form(loaded_at=str(time.time())), follow_redirects=False
        )

    assert response.status_code == 303
    send.assert_not_called()

    session = session_factory()
    try:
        row = session.scalar(select(ContactMessage))
    finally:
        session.close()
    assert row is not None
    assert row.is_spam is True


def test_rate_limit_fourth_submission_returns_429(client):
    with patch("app.main.send_contact_email"):
        statuses = [
            client.post("/contact", data=_form(), follow_redirects=False).status_code
            for _ in range(4)
        ]

    assert statuses == [303, 303, 303, 429]


def test_valid_submission_inserts_and_sends_email(client, session_factory):
    with patch("app.main.send_contact_email") as send:
        response = client.post("/contact", data=_form(), follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].endswith("?sent=1")
    send.assert_called_once()

    session = session_factory()
    try:
        row = session.scalar(select(ContactMessage))
    finally:
        session.close()
    assert row is not None
    assert row.is_spam is False
    assert row.email == "jane@example.com"
