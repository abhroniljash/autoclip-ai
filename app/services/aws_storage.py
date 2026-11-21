"""Private S3 object storage helpers. Uses the ECS task role, never embedded credentials."""
from __future__ import annotations

import os
from urllib.parse import urlparse

import boto3

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
S3_BUCKET = os.environ.get("S3_BUCKET", "").strip()
_s3 = None


def s3_client():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=AWS_REGION)
    return _s3


def enabled() -> bool:
    return bool(S3_BUCKET)


def upload_file(local_path: str, key: str, content_type: str | None = None) -> str:
    if not enabled():
        raise RuntimeError("S3_BUCKET is not configured.")
    extra = {"ContentType": content_type} if content_type else {}
    s3_client().upload_file(local_path, S3_BUCKET, key, ExtraArgs=extra)
    return f"s3://{S3_BUCKET}/{key}"


def parse_uri(uri: str) -> tuple[str, str] | None:
    if not uri or not uri.startswith("s3://"):
        return None
    parsed = urlparse(uri)
    if parsed.netloc != S3_BUCKET or not parsed.path.lstrip("/"):
        raise ValueError("S3 URI does not match the configured private bucket.")
    return parsed.netloc, parsed.path.lstrip("/")


def presigned_url(uri: str, expires_in: int = 600) -> str:
    parsed = parse_uri(uri)
    if not parsed:
        raise ValueError("Not an S3 object URI.")
    bucket, key = parsed
    return s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=max(60, min(expires_in, 3600)),
    )


def delete_prefix(prefix: str) -> None:
    if not enabled():
        return
    paginator = s3_client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if objects:
            s3_client().delete_objects(Bucket=S3_BUCKET, Delete={"Objects": objects})

def download_file(uri: str, destination: str) -> str:
    parsed = parse_uri(uri)
    if not parsed:
        raise ValueError("Not an S3 object URI.")
    bucket, key = parsed
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    s3_client().download_file(bucket, key, destination)
    return destination
