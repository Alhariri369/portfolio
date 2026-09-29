"""Cloudflare R2 storage client (S3-compatible)."""
from __future__ import annotations

import os
from functools import lru_cache

import boto3
from botocore.config import Config


@lru_cache(maxsize=1)
def get_s3_client():
    """Build (and cache) a boto3 S3 client pointed at Cloudflare R2."""
    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        service_name="s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def upload_fileobj(fileobj, key: str, content_type: str | None = None) -> str:
    """Upload a file-like object to R2 and return its public URL."""
    bucket = os.environ["R2_BUCKET"]
    extra = {"ContentType": content_type} if content_type else {}
    get_s3_client().upload_fileobj(fileobj, bucket, key, ExtraArgs=extra)
    return f"{public_url_base()}/{key.lstrip('/')}"


def delete_object(key: str) -> None:
    """Delete an object from R2 by key."""
    get_s3_client().delete_object(
        Bucket=os.environ["R2_BUCKET"], Key=key.lstrip("/")
    )


def public_url_base() -> str:
    """Base URL for public access (custom domain or r2.dev)."""
    return os.environ["R2_PUBLIC_URL"].rstrip("/")