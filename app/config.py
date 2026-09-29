"""Application configuration read from environment variables."""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent

# The database is remote (Neon Postgres) in production and SQLite for local dev.
# Never hardcode credentials - they come from the environment (.env in Docker).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Uploads location.
#   - Vercel: only /tmp is writable. It is ephemeral (wiped on cold start),
#     so treat this as temporary storage only.
#   - Docker: UPLOAD_DIR env var points to a mounted volume (e.g. /data/uploads).
#   - Local dev: falls back to app/static/uploads.

SITE_URL = os.getenv("BASE_URL", "https://hariri-dev.com").rstrip("/")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")

EMAIL_FROM = os.getenv("EMAIL_FROM", "portfolio@hariri-dev.com")
EMAIL_TO = os.getenv("EMAIL_TO", "moh.alhariri369@gmail.com")

CF_ANALYTICS_TOKEN = os.getenv("CF_ANALYTICS_TOKEN", "")