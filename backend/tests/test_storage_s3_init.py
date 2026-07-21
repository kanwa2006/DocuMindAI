"""Regression test for DEBUG_MASTER_PLAN H-5.

`S3StorageProvider.__init__` read `settings.AWS_REGION`, which was never
defined in `Settings` (`S3_REGION` is the real key) — selecting
`STORAGE_PROVIDER=s3` crashed with AttributeError at provider init.
"""
from unittest.mock import patch


def test_s3_provider_initializes_with_s3_region(monkeypatch):
    from app.core import storage as storage_module
    from app.core.config import settings

    monkeypatch.setattr(settings, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(settings, "S3_REGION", "ap-south-1")

    with patch.object(storage_module, "boto3") as mock_boto3:
        provider = storage_module.S3StorageProvider()

    assert provider.bucket == "test-bucket"
    _, kwargs = mock_boto3.client.call_args
    assert kwargs["region_name"] == "ap-south-1"


def test_settings_has_no_aws_region_attr():
    """Guard: nothing should reintroduce the phantom AWS_REGION key."""
    from app.core.config import settings

    assert not hasattr(settings, "AWS_REGION")
