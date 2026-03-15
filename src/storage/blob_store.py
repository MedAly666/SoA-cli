from __future__ import annotations

import os
from pathlib import Path


class BlobStore:
    """Optional MinIO/S3 uploader for large binary blobs.

    Configure with:
    - SOA_BLOB_ENDPOINT
    - SOA_BLOB_ACCESS_KEY
    - SOA_BLOB_SECRET_KEY
    - SOA_BLOB_BUCKET
    - SOA_BLOB_SECURE=true|false
    """

    def __init__(self) -> None:
        self.endpoint = os.getenv("SOA_BLOB_ENDPOINT", "")
        self.access_key = os.getenv("SOA_BLOB_ACCESS_KEY", "")
        self.secret_key = os.getenv("SOA_BLOB_SECRET_KEY", "")
        self.bucket = os.getenv("SOA_BLOB_BUCKET", "soa-cli")
        self.secure = os.getenv("SOA_BLOB_SECURE", "false").lower() == "true"
        self.enabled = bool(self.endpoint and self.access_key and self.secret_key)

    def upload(self, local_path: Path, object_name: str) -> str:
        if not self.enabled:
            return ""
        try:
            from minio import Minio
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("minio package is required for BlobStore") from exc

        client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )
        if not client.bucket_exists(self.bucket):
            client.make_bucket(self.bucket)
        client.fput_object(self.bucket, object_name, str(local_path))
        return f"s3://{self.bucket}/{object_name}"
