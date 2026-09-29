"""Optional smoke test for Cloudflare R2. Skips unless R2_* env vars are set."""
import io
import os
import urllib.request

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("R2_BUCKET"),
    reason="R2 env vars not configured",
)


def test_upload_and_fetch():
    from app.storage import upload_fileobj

    payload = b"hello r2"
    url = upload_fileobj(io.BytesIO(payload), "uploads/pytest-smoke.txt", "text/plain")

    with urllib.request.urlopen(url) as resp:
        assert resp.status == 200
        assert resp.read() == payload