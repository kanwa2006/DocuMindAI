import os
import asyncio
import logging
from pathlib import Path
from fastapi import UploadFile
import aiofiles
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)


class UnsafeStorageKey(ValueError):
    """A storage key that does not resolve inside the storage root."""


def validate_object_key(object_key: str) -> str:
    """Return `object_key` unchanged, or raise `UnsafeStorageKey`.

    H2 — `verify_upload` stored the CLIENT-SUPPLIED `object_key` verbatim as
    `Document.storage_path`, and three sinks then consumed it:

      • `Path(storage_path).stat()` in verify_upload — a file existence and
        size oracle for any path on the server
      • `LocalStorageProvider.download_file`, which treats an absolute key as
        a literal path — so the Celery worker would read ANY file into the RAG
        corpus, after which the attacker simply asks a question about it
      • `delete_document`, which calls `Path(storage_path).unlink()` —
        **arbitrary file delete** as whatever user the API runs as

    Neither upload endpoint needs the client to choose a location: the
    presigned route generates `workspaces/{ws}/{uuid}_{name}` and the local
    route writes under `STORAGE_PATH` and returns the absolute path it chose.
    The client is only ever echoing a value the SERVER produced, so validating
    that it still resolves inside the storage root costs nothing legitimate.

    Checks, in order:
      1. non-empty, no NUL byte (NUL truncates paths in some syscalls)
      2. `local://` prefix stripped, then treated as a relative key
      3. no `..` component — rejected before resolution, so a symlink cannot
         launder it
      4. resolved path must be contained by the resolved storage root

    S3 keys are relative and land in step 3/4 against the local root, which is
    the correct shape check for them too: `workspaces/…` passes, `../…` and
    `/etc/passwd` do not.
    """
    if not object_key or not object_key.strip():
        raise UnsafeStorageKey("storage key is empty")
    if "\x00" in object_key:
        raise UnsafeStorageKey("storage key contains a NUL byte")

    key = object_key[len("local://"):] if object_key.startswith("local://") else object_key

    # Reject traversal BEFORE resolving: resolution can follow a symlink out
    # of the root and back, and we would rather refuse than reason about it.
    if ".." in Path(key.replace("\\", "/")).parts:
        raise UnsafeStorageKey("storage key contains a parent-directory segment")

    root = Path(settings.STORAGE_PATH).resolve()
    candidate = Path(key)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()

    if not resolved.is_relative_to(root):
        raise UnsafeStorageKey("storage key resolves outside the storage root")

    return object_key


class BaseStorageProvider:
    async def save_upload_file(self, upload_file: UploadFile, object_key: str) -> str:
        """Saves a file asynchronously and returns the storage URI."""
        raise NotImplementedError
        
    def download_file(self, object_key: str, local_path: str) -> None:
        """Downloads a file synchronously (safe for Celery worker threads)."""
        raise NotImplementedError

    def save_file_stream_sync(self, file_stream, object_key: str) -> str:
        """Saves a binary file stream synchronously (safe for Celery workers)."""
        raise NotImplementedError

class LocalStorageProvider(BaseStorageProvider):
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    async def save_upload_file(self, upload_file: UploadFile, object_key: str) -> str:
        # Flatten directory structure for local mock by replacing / with _
        safe_name = object_key.replace("/", "_")
        file_path = self.base_dir / safe_name
        
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await upload_file.read(1024 * 1024):
                await out_file.write(content)
        return f"local://{safe_name}"

    def save_file_stream_sync(self, file_stream, object_key: str) -> str:
        safe_name = object_key.replace("/", "_")
        file_path = self.base_dir / safe_name
        with open(file_path, 'wb') as out_file:
            out_file.write(file_stream.read())
        return f"local://{safe_name}"

    def download_file(self, object_key: str, local_path: str) -> None:
        # BUG-011 FIX: The upload_local endpoint stores the absolute filesystem path
        # as storage_path (e.g. /srv/storage/workspace/abc_file.pdf on Linux, or
        # C:\storage\workspace\abc_file.pdf on Windows).
        # The old code did: self.base_dir / object_key.replace("local://", "")
        # When object_key is an absolute path with no "local://" prefix, this
        # produces a nonsensical path from joining base_dir with an absolute path.
        #
        # Decision tree:
        #   1. "local://..." prefix → strip prefix, join with base_dir (original local:// convention)
        #   2. Already an absolute path → use directly (upload_local stores absolute paths)
        #   3. Anything else → treat as relative, join with base_dir
        import os
        # H2 defence in depth: the write path (verify_upload) now validates the
        # key, but rows written BEFORE that fix still carry whatever the client
        # sent. Re-check here so a pre-existing bad row cannot be read either.
        validate_object_key(object_key)

        if object_key.startswith("local://"):
            filename = object_key[len("local://"):]
            src_path = self.base_dir / filename
        elif os.path.isabs(object_key):
            src_path = Path(object_key)
        else:
            src_path = self.base_dir / object_key

        if not src_path.exists():
            raise FileNotFoundError(f"Local file not found: {src_path}")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(src_path, "rb") as src, open(local_path, "wb") as dst:
            dst.write(src.read())

class S3StorageProvider(BaseStorageProvider):
    def __init__(self):
        self.bucket = settings.S3_BUCKET
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            # H-5: the config key is S3_REGION (settings.AWS_REGION never
            # existed — selecting STORAGE_PROVIDER=s3 crashed at init).
            region_name=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL
        )
        
    async def save_upload_file(self, upload_file: UploadFile, object_key: str) -> str:
        try:
            # Execute blocking boto3 network call in threadpool to prevent ASGI blocking
            await asyncio.to_thread(
                self.s3_client.upload_fileobj,
                upload_file.file,
                self.bucket,
                object_key,
                ExtraArgs={'ContentType': upload_file.content_type}
            )
            return f"s3://{self.bucket}/{object_key}"
        except ClientError as e:
            logger.error(f"[Storage] S3 Upload failed: {e}")
            raise
            
    def save_file_stream_sync(self, file_stream, object_key: str) -> str:
        try:
            self.s3_client.upload_fileobj(file_stream, self.bucket, object_key)
            return f"s3://{self.bucket}/{object_key}"
        except ClientError as e:
            logger.error(f"[Storage] S3 Stream Upload failed: {e}")
            raise
            
    def download_file(self, object_key: str, local_path: str) -> None:
        try:
            if object_key.startswith("s3://"):
                object_key = object_key.split("/", 3)[-1]
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3_client.download_file(self.bucket, object_key, local_path)
        except ClientError as e:
            logger.error(f"[Storage] S3 Download failed: {e}")
            raise

class StorageFactory:
    _instance = None
    
    @classmethod
    def get_provider(cls) -> BaseStorageProvider:
        if cls._instance is None:
            if settings.STORAGE_PROVIDER == "s3":
                cls._instance = S3StorageProvider()
            else:
                cls._instance = LocalStorageProvider(settings.STORAGE_PATH)
        return cls._instance

storage_service = StorageFactory.get_provider()
