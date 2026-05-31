from __future__ import annotations

from flask import current_app


def get_s3_client():
    """Return a cached boto3 S3 client with SigV4, creating it on first call."""
    if "s3_client" not in current_app.extensions:
        import boto3
        from botocore.config import Config

        cfg = current_app.config
        client = boto3.client(
            "s3",
            region_name=cfg["AWS_REGION"],
            aws_access_key_id=cfg["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=cfg["AWS_SECRET_ACCESS_KEY"],
            config=Config(signature_version="s3v4"),
        )
        current_app.extensions["s3_client"] = client

    return current_app.extensions["s3_client"]
