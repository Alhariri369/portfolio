"""Daily offsite backup to Cloudflare R2 (run with: python -m app.backup).

Runs once on start, then every 24 hours. It dumps the Postgres database with
pg_dump, tars the dump plus the uploads directory, uploads the archive to R2,
and prunes backups older than 30 days. When DATABASE_URL points at SQLite
(local dev) the dump step is skipped.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

import boto3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("backup")

INTERVAL_SECONDS = 24 * 3600
RETENTION_DAYS = 30


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _r2_client():
    account_id = os.getenv("R2_ACCOUNT_ID", "")
    access_key = os.getenv("R2_ACCESS_KEY_ID", "")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "")
    if not account_id:
        raise RuntimeError("R2_ACCOUNT_ID is not set")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )


def _dump_database(url: str, destination: Path) -> None:
    pg_url = url.replace("postgresql+psycopg://", "postgresql://")
    with destination.open("wb") as handle:
        subprocess.run(
            ["pg_dump", "--dbname", pg_url],
            stdout=handle,
            check=True,
        )


def _make_archive(dump_path: Path, uploads_dir: Path, workdir: Path) -> Path:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = workdir / f"backup-{timestamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        if dump_path.exists():
            tar.add(dump_path, arcname="db.dump")
        if uploads_dir.exists():
            tar.add(uploads_dir, arcname="uploads")
    return archive


def _prune(client, bucket: str, now: dt.datetime) -> None:
    cutoff = now - dt.timedelta(days=RETENTION_DAYS)
    response = client.list_objects_v2(Bucket=bucket)
    for obj in response.get("Contents", []):
        last_modified = obj["LastModified"]
        if last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=dt.timezone.utc)
        if last_modified < cutoff:
            key = obj["Key"]
            client.delete_object(Bucket=bucket, Key=key)
            logger.info("Deleted old backup %s", key)


def run_once() -> None:
    url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    uploads_dir = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))
    bucket = os.getenv("R2_BUCKET", "")

    if _is_sqlite(url):
        logger.info("DATABASE_URL is SQLite; skipping database dump (local dev)")
        return

    if not bucket:
        raise RuntimeError("R2_BUCKET is not set")

    client = _r2_client()
    with tempfile.TemporaryDirectory(prefix="portfolio-backup-") as tmp:
        workdir = Path(tmp)
        dump_path = workdir / "db.dump"
        logger.info("Dumping database...")
        _dump_database(url, dump_path)
        logger.info("Creating archive...")
        archive = _make_archive(dump_path, uploads_dir, workdir)
        logger.info("Uploading %s to R2 bucket %s", archive.name, bucket)
        client.upload_file(str(archive), bucket, archive.name)
        logger.info("Upload complete")
    _prune(client, bucket, dt.datetime.now(dt.timezone.utc))


def main() -> None:
    logger.info("Backup service starting (every %s seconds)", INTERVAL_SECONDS)
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("Backup run failed")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
