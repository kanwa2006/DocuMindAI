import os
import time
import shutil

def get_user_storage_dir(user_id: int) -> str:
    from backend.config import STORAGE_BASE
    path = os.path.join(STORAGE_BASE, str(user_id), "files")
    os.makedirs(path, exist_ok=True)
    return path

def get_images_dir(user_id: int) -> str:
    from backend.config import STORAGE_BASE
    path = os.path.join(STORAGE_BASE, str(user_id), "images")
    os.makedirs(path, exist_ok=True)
    return path

def get_index_dir(user_id: int) -> str:
    from backend.config import STORAGE_BASE
    path = os.path.join(STORAGE_BASE, str(user_id), "index")
    os.makedirs(path, exist_ok=True)
    return path

def save_uploaded_file(user_id: int, filename: str, content: bytes) -> str:
    storage_dir = get_user_storage_dir(user_id)
    file_path = os.path.join(storage_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path

def delete_document_file(user_id: int, filename: str):
    """
    Delete a document file. On Windows, file may be locked by OCR/indexing process.
    Retries up to 5 times with delay before giving up gracefully.
    """
    storage_dir = get_user_storage_dir(user_id)
    file_path = os.path.join(storage_dir, filename)

    if not os.path.exists(file_path):
        return  # Already gone, no error

    # Try up to 5 times (handles Windows file lock from background indexing)
    for attempt in range(5):
        try:
            os.remove(file_path)
            print(f"[Storage] Deleted: {filename}")
            return
        except PermissionError:
            if attempt < 4:
                print(f"[Storage] File locked, retry {attempt+1}/5: {filename}")
                time.sleep(0.5)
            else:
                # Last resort on Windows — mark for deletion and continue
                # DB record will be deleted, file cleanup on next restart
                print(f"[Storage] WARNING: Could not delete locked file: {filename}")
                # Don't raise — let the DB deletion proceed
                return
        except Exception as e:
            print(f"[Storage] Delete error: {e}")
            return
