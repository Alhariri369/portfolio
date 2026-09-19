"""Translation loading and lookup helpers."""
from __future__ import annotations

import contextvars
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "translations"

translations: dict[str, dict[str, str]] = {"en": {}, "ar": {}}

# Language for the current request. Set by the middleware/render helper so the
# Jinja globals t() and pick() know which language to use.
_current_lang = contextvars.ContextVar("portfolio_lang", default="en")


def load_translations() -> None:
    """Load en.json and ar.json once at startup."""
    for lang in ("en", "ar"):
        path = TRANSLATIONS_DIR / f"{lang}.json"
        with path.open(encoding="utf-8") as handle:
            translations[lang] = json.load(handle)
    logger.info("Loaded translations for %s", ", ".join(translations))


def get_lang(request_or_path) -> str:
    """Return 'ar' for /ar... paths, otherwise 'en'."""
    if isinstance(request_or_path, str):
        path = request_or_path
    else:
        path = request_or_path.url.path
    if path == "/ar" or path.startswith("/ar/"):
        return "ar"
    return "en"


def translate(key: str, lang: str = "en") -> str:
    """Return a UI string; log and return the key when missing."""
    table = translations.get(lang) or {}
    if key not in table:
        logger.warning("Missing translation key %r for language %s", key, lang)
        return key
    return table[key]


def pick_localized(obj, field: str, lang: str) -> str:
    """Pick `field_{lang}` off an object, falling back to English."""
    if obj is None:
        return ""
    value = getattr(obj, f"{field}_{lang}", None)
    if value is None or value == "":
        value = getattr(obj, f"{field}_en", None)
    return value or ""


def t(key: str) -> str:
    """Jinja global: translate using the current request language."""
    return translate(key, _current_lang.get())


def pick(obj, field: str) -> str:
    """Jinja global: pick the localized field using the current language."""
    return pick_localized(obj, field, _current_lang.get())


# Load immediately so the application and tests always have strings available.
load_translations()
