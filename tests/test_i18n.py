"""i18n key parity and bilingual seed content checks."""
from __future__ import annotations

from app.i18n import translations


def test_translation_key_parity():
    assert set(translations["en"]) == set(translations["ar"])


def _bilingual_pairs(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.endswith("_en") and isinstance(value, str):
                yield value, obj.get(key[:-3] + "_ar")
            else:
                yield from _bilingual_pairs(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _bilingual_pairs(item)


def test_every_english_seed_field_has_arabic():
    from app.seed import SEED

    missing = []
    for en, ar in _bilingual_pairs(SEED):
        if not isinstance(ar, str):
            missing.append(f"missing Arabic for: {en!r}")
        elif en.strip() and not ar.strip():
            missing.append(f"empty Arabic for: {en!r}")

    assert missing == []
