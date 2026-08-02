"""Regression guard for final_audit H2.

`verify_upload` stored the CLIENT-SUPPLIED `object_key` verbatim as
`Document.storage_path`. Three sinks consumed it:

  • `Path(storage_path).stat()` in verify_upload — a file existence and size
    oracle for any path on the server
  • `LocalStorageProvider.download_file`, which treats an absolute key as a
    literal path, so the Celery worker would read ANY file into the RAG
    corpus — after which the attacker just asks a question about it
  • `delete_document` calling `Path(storage_path).unlink()` — an ARBITRARY
    FILE DELETE as whatever user the API runs as

Neither upload route needs the client to choose a location: the presigned
route generates `workspaces/{ws}/{uuid}_{name}`, and the local route writes
under STORAGE_PATH and returns the absolute path it chose. The client only
ever echoes a value the SERVER produced, so requiring the key to resolve
inside the storage root rejects nothing legitimate — which is what makes this
fix safe to apply at the choke point rather than case by case.
"""
import pathlib

import pytest

from app.core.config import settings
from app.core.storage import UnsafeStorageKey, validate_object_key


def _root() -> pathlib.Path:
    return pathlib.Path(settings.STORAGE_PATH).resolve()


# ── Keys the server itself produces must keep working ────────────────────────

def test_presigned_style_relative_key_is_accepted():
    key = "workspaces/legal/6f1c1a4e_contract.pdf"
    assert validate_object_key(key) == key


def test_local_upload_absolute_path_under_the_root_is_accepted():
    key = str(_root() / "legal" / "abc123_handbook.pdf")
    assert validate_object_key(key) == key


def test_local_uri_scheme_is_accepted():
    key = "local://workspaces_general_report.pdf"
    assert validate_object_key(key) == key


# ── The three attack shapes ──────────────────────────────────────────────────

@pytest.mark.parametrize(
    "evil",
    [
        "/etc/passwd",
        "/etc/shadow",
        "C:\\Windows\\win.ini",
        "../../../../etc/passwd",
        "workspaces/../../../etc/passwd",
        "local://../../../etc/passwd",
        "workspaces/legal/..\\..\\..\\windows\\win.ini",
    ],
)
def test_paths_outside_the_storage_root_are_rejected(evil):
    with pytest.raises(UnsafeStorageKey):
        validate_object_key(evil)


@pytest.mark.parametrize("bad", ["", "   ", "some/path\x00.pdf"])
def test_empty_and_nul_keys_are_rejected(bad):
    """A NUL byte truncates the path in some syscalls — reject, don't sanitise."""
    with pytest.raises(UnsafeStorageKey):
        validate_object_key(bad)


def test_traversal_is_rejected_before_resolution():
    """A `..` segment is refused on sight, not reasoned about after resolving.

    Resolution can follow a symlink out of the root and back in again; refusing
    the segment outright removes the need to be right about that.
    """
    with pytest.raises(UnsafeStorageKey):
        validate_object_key(str(_root() / ".." / "escaped.pdf"))


# ── The sinks must call the validator, not just the write path ───────────────

def test_download_file_validates_before_reading():
    """Rows written BEFORE the write-path fix still carry unvalidated keys."""
    import inspect

    from app.core.storage import LocalStorageProvider

    src = inspect.getsource(LocalStorageProvider.download_file)
    assert "validate_object_key" in src, (
        "download_file does not validate its key. The write path is fixed, but "
        "pre-existing rows still hold whatever the client sent, and this is the "
        "sink that reads an arbitrary file into the RAG corpus (H2)."
    )


def test_delete_document_validates_before_unlinking():
    import inspect

    from app.api.v1.endpoints import documents

    src = inspect.getsource(documents.delete_document)
    assert "validate_object_key" in src, (
        "delete_document unlinks storage_path without validating it — this is "
        "the arbitrary-file-delete sink (H2)."
    )


def test_verify_upload_validates_the_client_supplied_key():
    import inspect

    from app.api.v1.endpoints import documents

    src = inspect.getsource(documents.verify_upload)
    assert "validate_object_key" in src, (
        "verify_upload stores request.object_key without validation — this is "
        "the source of H2; every sink downstream inherits it."
    )
