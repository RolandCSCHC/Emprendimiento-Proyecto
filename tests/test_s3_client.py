"""Tests del S3 Client (mockeando S3 con moto)."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from app.services.aws import s3_client

BUCKET = "test-bucket"
REGION = "us-east-1"


@pytest.fixture
def s3_setup(app):
    """Crea un bucket de prueba con un objeto existente."""
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET)
        client.put_object(Bucket=BUCKET, Key="existe.mp4", Body=b"data")
        yield


def test_check_object_exists_true(s3_setup):
    assert s3_client.check_object_exists(BUCKET, "existe.mp4") is True


def test_check_object_exists_false(s3_setup):
    assert s3_client.check_object_exists(BUCKET, "no-existe.mp4") is False


def test_get_s3_uri():
    assert s3_client.get_s3_uri(BUCKET, "carpeta/video.mp4") == (
        "s3://test-bucket/carpeta/video.mp4"
    )


def test_generate_presigned_url(s3_setup):
    url = s3_client.generate_presigned_url(BUCKET, "existe.mp4", expires_in=60)
    assert url is not None
    assert "existe.mp4" in url
